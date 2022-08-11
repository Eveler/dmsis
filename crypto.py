# -*- encoding: utf-8 -*-
from encodings.base64_codec import base64_decode

from OpenSSL import crypto
from OpenSSL.crypto import _ffi, X509, _lib, _new_mem_buf, _bio_to_string


def get_certificates(p7data):
    """
    https://github.com/pyca/pyopenssl/pull/367/files#r67300900

    Returns all certificates for the PKCS7 structure, if present. Only
    objects of type ''signedData'' or ''signedAndEnvelopedData'' can embed
    certificates.

    :return: The certificates in the PKCS7, or :const:'None' if
        there are none.
    :rtype: :class:'tuple' of :class:'X509' or :const:'None'
    """
    certs = _ffi.NULL
    if p7data.type_is_signed():
        certs = p7data._pkcs7.d.sign.cert
        # print(_lib.X509_get_subject_name(_lib.sk_X509_value(certs, 0)))
    elif p7data.type_is_signedAndEnveloped():
        certs = p7data._pkcs7.d.signed_and_enveloped.cert

    pycerts = []
    for i in range(_lib.sk_X509_num(certs)):
        pycert = X509.__new__(X509)
        pycert._x509 = _lib.sk_X509_value(certs, i)
        pycerts.append(pycert)
        if not 'Администрация Уссурийского городского округа' in [v.value for v in pycert.to_cryptography().subject]:
            print(pycert.to_cryptography().subject)

    if not pycerts:
        return None
    return tuple(pycerts)


def clean_pkcs7(p7data, subject='Администрация Уссурийского городского округа'):
    """
    Removes all certificates from the PKCS7 structure, if certificate subject not contains `subject`.
    """
    if not p7data:
        return p7data
    p7data = crypto.load_pkcs7_data(crypto.FILETYPE_ASN1,
                                    base64_decode(p7data.encode())[0] if isinstance(p7data, str) else p7data)
    certs = _ffi.NULL
    if p7data.type_is_signed():
        certs = p7data._pkcs7.d.sign.cert
    elif p7data.type_is_signedAndEnveloped():
        certs = p7data._pkcs7.d.signed_and_enveloped.cert

    for i in range(_lib.sk_X509_num(certs)):
        pycert = X509.__new__(X509)
        pycert._x509 = _lib.sk_X509_value(certs, i)
        if subject.upper() in [v.value.upper() for v in pycert.to_cryptography().subject]:
            sk = _lib.sk_X509_new_null()
            _lib.sk_X509_push(sk, pycert._x509)
            if p7data.type_is_signed():
                p7data._pkcs7.d.sign.cert = sk
            elif p7data.type_is_signedAndEnveloped():
                p7data._pkcs7.d.signed_and_enveloped.cert = sk

    bp = _new_mem_buf()
    _lib.PEM_write_bio_PKCS7(bp, p7data._pkcs7)
    return _bio_to_string(bp).replace(b'-----BEGIN PKCS7-----', b'').replace(
                                    b'-----END PKCS7-----', b'').replace(b'\r', b'').replace(b'\n', b'')


if __name__ == '__main__':
    for cert in get_certificates(ci):
        print(cert.get_serial_number())
        print(cert.get_signature_algorithm().decode())
        print('Valid:', cert.to_cryptography().not_valid_before, 'to',
              cert.to_cryptography().not_valid_after)
        print(cert.get_extension_count())
        print(cert.subject_name_hash())
        print(cert.to_cryptography().subject)
        print('*' * 20)
        if 'Администрация Уссурийского городского округа' in [v.value for v in cert.to_cryptography().subject]:
            with open('C:\\Users\\Администратор\\Desktop\\1111111.crt', 'wb') as f:
                f.write(crypto.dump_certificate(crypto.FILETYPE_PEM, cert))
