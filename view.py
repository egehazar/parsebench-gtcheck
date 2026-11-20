"""Render a test page (or a vertical slice of it) to work/view/<name>.png for a visual check."""
import os, sys
import pypdfium2 as pdfium
GT = os.path.join(os.path.dirname(__file__), 'data', 'gt_main')

def render(doc_rel, out, scale=1.5, top=0.0, bottom=1.0, left=0.0, right=1.0, page_index=0):
    doc = pdfium.PdfDocument(os.path.join(GT, doc_rel))
    img = doc[page_index].render(scale=scale).to_pil()
    W, H = img.size
    img = img.crop((int(left * W), int(top * H), int(right * W), int(bottom * H)))
    os.makedirs(os.path.join(os.path.dirname(__file__), 'work', 'view'), exist_ok=True)
    p = os.path.join(os.path.dirname(__file__), 'work', 'view', out + '.png'); img.save(p); doc.close()
    print(p, img.size)

if __name__ == '__main__':
    a = sys.argv
    render(a[1], a[2], float(a[3]) if len(a) > 3 else 1.5, *(float(x) for x in a[4:8]))
