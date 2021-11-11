/*
 * Created by SharpDevelop.
 * Date: 23.11.2017
 * Time: 0:03
 * 
 * To change this template use Tools | Options | Coding | Edit Standard Headers.
 */
using System;
using System.Security.Cryptography.X509Certificates;
using System.Security.Cryptography.Xml;
using System.Text;
using System.Xml;
using System.IO;
using CryptoPro.Sharpei.Xml;

namespace xmlsigner
{
	class Program
	{
		public static void Main(string[] args)
		{
			string serial = "";
			if(args.Length > 1)
			{
				serial = args[1];
			}
			string xmlStr;
			xmlStr = Console.In.ReadToEnd();
						
			var cert = GetCertificate(serial);
			string res = SignXmlFile(xmlStr, cert);
			Console.Write(res);
		}
		
		private static X509Certificate2 GetCertificate(string serial=null)
			// Get system sertificate by serial number, or very first if serial is null or empty
        {
			var store = new X509Store();
            store.Open(OpenFlags.ReadOnly);
            X509Certificate2 card = null;
            if(!string.IsNullOrEmpty(serial))
            {
            	string sn = serial.Replace(" ", "");
	            foreach (X509Certificate2 cert in store.Certificates)
    	        {
					if(cert.SerialNumber == sn)
    	            {
    	                card = cert;
    	                break;
    	            }
    	        }
            }
            else card = store.Certificates[0];
   	        store.Close();

   	        return card;
        }
		
		private static string SignXmlFile(string xmlStr, X509Certificate2 cert)
			// Sing xml with GOST algo according Minsvyaz recomendations
		{
			var xmlDoc = new XmlDocument();
			xmlDoc.PreserveWhitespace = true;
			xmlDoc.LoadXml(xmlStr);
			var signedXml = new SignedXml(xmlDoc)
			{
				SigningKey = cert.PrivateKey
			};
			signedXml.SafeCanonicalizationMethods.Add("urn://smev-gov-ru/xmldsig/transform");
			
			var reference = new Reference("#SIGNED_BY_CALLER");
//			reference.DigestMethod = CPSignedXml.XmlDsigGost3411UrlObsolete;
//			reference.DigestMethod = CPSignedXml2012_256.XmlDsigGost3411Url;
			reference.DigestMethod = "urn:ietf:params:xml:ns:cpxmlsec:algorithms:gostr34112012-256";
			reference.AddTransform(new XmlDsigExcC14NTransform());
			reference.AddTransform(new XmlDsigSmevTransform());
			reference.AddTransform(new XmlDsigEnvelopedSignatureTransform());
			
			var keyInfo = new KeyInfo();
			keyInfo.AddClause(new KeyInfoX509Data(cert));

			signedXml.AddReference(reference);
			signedXml.KeyInfo = keyInfo;
			signedXml.SignedInfo.CanonicalizationMethod = SignedXml.XmlDsigExcC14NTransformUrl;
//			signedXml.SignedInfo.SignatureMethod = CPSignedXml.XmlDsigGost3410_2012_256Url;
			signedXml.SignedInfo.SignatureMethod = "urn:ietf:params:xml:ns:cpxmlsec:algorithms:gostr34102012-gostr34112012-256";
			
			signedXml.ComputeSignature();
			if (!signedXml.CheckSignature()) throw new ApplicationException("Неверная подпись!!!");
			
			var res = new StringBuilder();
			var tw = new StringWriter(res);
			var w = new XmlTextWriter(tw);
			signedXml.GetXml().WriteTo(w);
			return res.ToString();
		}
	}
}