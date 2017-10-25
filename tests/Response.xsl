<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet xmlns:xsl="http://www.w3.org/1999/XSL/Transform" xmlns:xs="http://www.w3.org/2001/XMLSchema" version="2.0" xmlns:ns1="urn://augo/smev/uslugi/1.0.0">
	<xsl:template match="ns1:Declar">
		<xsl:result-document>
			<ns1:requestResponse>
				<ns1:declar_number>23156/564/5611Д</ns1:declar_number>
				<ns1:register_date>2008-09-29</ns1:register_date>
				<ns1:result>ACCEPTED</ns1:result>
			</ns1:requestResponse>
		</xsl:result-document>
		<xsl:result-document>
			<ns1:requestResponse>
				<ns1:declar_number>23156/564/5611Д</ns1:declar_number>
				<ns1:register_date>2008-09-29</ns1:register_date>
				<ns1:result>INTERMEDIATE</ns1:result>
				<ns1:AppliedDocument>
					<ns1:title>Уведомление</ns1:title>
					<ns1:number>08-65/2569</ns1:number>
					<ns1:date>2008-09-30</ns1:date>
					<ns1:url>https://123.45.67.89/download/AE4567BC</ns1:url>
					<ns1:url_valid_until>2008-10-03T01:41:17.783+04:00</ns1:url_valid_until>
				</ns1:AppliedDocument>
			</ns1:requestResponse>
		</xsl:result-document>
		<xsl:result-document>
			<ns1:requestResponse>
				<ns1:declar_number>23156/564/5611Д</ns1:declar_number>
				<ns1:register_date>2008-09-29</ns1:register_date>
				<ns1:result>INFO</ns1:result>
				<ns1:text>Решение отправлено на согласование</ns1:text>
			</ns1:requestResponse>
		</xsl:result-document>
		<xsl:result-document>
			<ns1:requestResponse>
				<ns1:declar_number>23156/564/5611Д</ns1:declar_number>
				<ns1:register_date>2008-09-29</ns1:register_date>
				<ns1:result>FINAL</ns1:result>
				<ns1:AppliedDocument>
					<ns1:title>Постановление</ns1:title>
					<ns1:number>1263-НПА</ns1:number>
					<ns1:date>2008-10-10</ns1:date>
					<ns1:url>https://123.45.67.89/download/AE4567BC</ns1:url>
					<ns1:url_valid_until>2008-10-15T01:41:17.783+04:00</ns1:url_valid_until>
				</ns1:AppliedDocument>
			</ns1:requestResponse>
		</xsl:result-document>
	</xsl:template>
</xsl:stylesheet>
