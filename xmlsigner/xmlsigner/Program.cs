/*
 * Created by SharpDevelop.
 * Date: 23.11.2017
 * Time: 0:03
 * 
 * To change this template use Tools | Options | Coding | Edit Standard Headers.
 */
using System;
//using System.Security.Cryptography;
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
			
//			Console.Write(xmlStr);
			
//			xmlStr = "<soap-env:Envelope xmlns:soap-env=\"http://schemas.xmlsoap.org/soap/envelope/\"><soap-env:Body>" +
//				"<ns0:GetRequestRequest xmlns:ns0=\"urn://x-artefacts-smev-gov-ru/services/message-exchange/types/1.2\">" +
//				"<ns1:MessageTypeSelector xmlns:ns1=\"urn://x-artefacts-smev-gov-ru/services/message-exchange/types/basic/1.2\" Id=\"SIGNED_BY_CALLER\">" +
//				"<ns1:Timestamp>2017-11-22T00:54:55.936780</ns1:Timestamp></ns1:MessageTypeSelector>" +
//				"<ns0:CallerInformationSystemSignature><ds:Signature xmlns:ds=\"http://www.w3.org/2000/09/xmldsig#\"><ds:SignedInfo>" +
//				"<ds:CanonicalizationMethod Algorithm=\"http://www.w3.org/2001/10/xml-exc-c14n#\"/>" +
//				"<ds:SignatureMethod Algorithm=\"http://www.w3.org/2001/04/xmldsig-more#gostr34102001-gostr3411\"/>" +
//				"<ds:Reference URI=\"#SIGNED_BY_CALLER\"><ds:Transforms><ds:Transform Algorithm=\"http://www.w3.org/2001/10/xml-exc-c14n#\"/>" +
//				"<ds:Transform Algorithm=\"urn://smev-gov-ru/xmldsig/transform\"/></ds:Transforms>" +
//				"<ds:DigestMethod Algorithm=\"http://www.w3.org/2001/04/xmldsig-more#gostr3411\"/><ds:DigestValue/>" +
//				"</ds:Reference></ds:SignedInfo><ds:SignatureValue/><ds:KeyInfo><ds:X509Data><ds:X509Certificate/></ds:X509Data></ds:KeyInfo></ds:Signature>" +
//				"</ns0:CallerInformationSystemSignature></ns0:GetRequestRequest></soap-env:Body></soap-env:Envelope>";
			
//			xmlStr = "<ns1:MessageTypeSelector xmlns:ns1=\"urn://x-artefacts-smev-gov-ru/services/message-exchange/types/basic/1.2\" Id=\"SIGNED_BY_CALLER\">" +
//				"<ns1:Timestamp>2017-11-22T00:54:55.936780</ns1:Timestamp></ns1:MessageTypeSelector>";
			
//			xmlStr = "<ns1:AckTargetMessage xmlns=\"urn://x-artefacts-smev-gov-ru/services/message-exchange/types/1.2\" " +
//				"xmlns:ns1=\"urn://x-artefacts-smev-gov-ru/services/message-exchange/types/basic/1.2\" " +
//				"Id=\"SIGNED_BY_CALLER\" accepted=\"true\">099f69d3-eba6-11e7-a22e-a45d36c7706f</ns1:AckTargetMessage>";
			
			var cert = GetCertificate(serial);
			string res = SignXmlFile(xmlStr, cert);
			Console.Write(res);
		}
		
		private static X509Certificate2 GetCertificate(string serial=null)
        {
//            var store = new X509Store(StoreName.My, StoreLocation.CurrentUser);
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
			reference.DigestMethod = CPSignedXml.XmlDsigGost3411UrlObsolete; 
			reference.AddTransform(new XmlDsigExcC14NTransform());
			reference.AddTransform(new XmlDsigSmevTransform());
			reference.AddTransform(new XmlDsigEnvelopedSignatureTransform());
			
			var keyInfo = new KeyInfo();
			keyInfo.AddClause(new KeyInfoX509Data(cert));

			signedXml.AddReference(reference);
			signedXml.KeyInfo = keyInfo;
			signedXml.SignedInfo.CanonicalizationMethod = SignedXml.XmlDsigExcC14NTransformUrl;
			signedXml.SignedInfo.SignatureMethod = CPSignedXml.XmlDsigGost3410UrlObsolete;
			
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