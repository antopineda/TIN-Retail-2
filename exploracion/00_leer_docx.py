# Solo lectura: extrae texto (párrafos y tablas en orden) de los .docx del grupo
import zipfile, re, sys
from xml.etree import ElementTree as ET
W = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
def texto(path):
    xml = zipfile.ZipFile(path).read('word/document.xml')
    body = ET.fromstring(xml).find(W+'body')
    out = []
    for el in body:
        if el.tag == W+'p':
            style = el.find(f'{W}pPr/{W}pStyle')
            s = style.get(W+'val') if style is not None else ''
            t = ''.join(x.text or '' for x in el.iter(W+'t'))
            if t.strip() or s: out.append((f'[{s}] ' if s else '') + t)
        elif el.tag == W+'tbl':
            for tr in el.iter(W+'tr'):
                out.append(' | '.join(''.join(x.text or '' for x in tc.iter(W+'t')) for tc in tr.iter(W+'tc')))
            out.append('[/tabla]')
    return '\n'.join(out)
for p in sys.argv[1:]:
    print('='*20, p); print(texto(p))
