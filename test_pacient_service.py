from typing import Dict, Any
from clients.fer_client import fer_client
from lxml import etree
from typing import List, TypedDict, Optional
from datetime import datetime, timedelta

namespaces = {
    'soap': 'http://schemas.xmlsoap.org/soap/envelope/',
    'ns': 'http://www.rt-eu.ru/med/er/v2_0'
}
session_id = "f0835f9b-3eb7-471a-b2e4-c7b538c90ca2"
oid = "1.2.643.5.1.13.13.12.2.72.7326.0.20901"
current_date = datetime.now().date()
end_date = current_date + timedelta(days=7)
date_start = current_date.strftime('%Y-%m-%d')
date_end = end_date.strftime('%Y-%m-%d')

print("\n\n")
print({
        'session_id': session_id,
        'post_id': 54,
        'oid': oid,
        'date_start': date_start,
        'date_end': date_end,
    })

response = fer_client.send('GetMOResourceInfoRequest', {
    'session_id': session_id,
    'post_id': 54,
    'oid': oid,
    'date_start': date_start,
    'date_end': date_end,
})

root = etree.fromstring(response)
print(etree.tostring(root, pretty_print=True, encoding='unicode'))

resource_elements = root.xpath(
    '//ns:GetMOResourceInfoResponse/ns:MO_Resource_List/ns:MO_Available/ns:Resource_Available/ns:Resource',
    namespaces=namespaces
)

print(resource_elements)