import os, re, io, zipfile, tempfile, subprocess, json, csv, datetime
from pathlib import Path
from flask import Flask, request, send_file, render_template, jsonify

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 60 * 1024 * 1024
MAX_FILES = 20
CSV_COLUMNS = ['file name','title','description','country','color','keywords']

def run(*args):
    return subprocess.run(['exiftool', *args], capture_output=True, text=True, timeout=45)

def valid_eps(data):
    return data.startswith(b'%!PS-Adobe') or data.startswith(b'\xc5\xd0\xd3\xc6')

def bounds(data):
    pos = data.find(b'%!PS-Adobe')
    if pos < 0: return None
    m = re.search(rb'(?m)^%%BoundingBox:\s*([^\r\n]+)', data[pos:pos+8192])
    return m.group(1) if m else None

def meta(path):
    try:
        p = run('-j', '-G1', '-a', '-s', str(path))
    except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
        return {'error': 'ExifTool unavailable: ' + str(exc)}
    if p.returncode:
        return {'error': p.stderr.strip() or 'ExifTool failed'}
    try:
        raw = json.loads(p.stdout)[0]
    except (ValueError, IndexError, TypeError):
        return {'error': 'Could not parse metadata'}
    aliases = {
        'Title': ['XMP-dc:Title','IPTC:Headline','IPTC:ObjectName','PostScript:Title','PDF:Title'],
        'Description': ['XMP-dc:Description','IPTC:Caption-Abstract','PostScript:Description','PDF:Subject'],
        'Subject': ['XMP-dc:Subject','IPTC:Keywords','XMP-photoshop:Keywords'],
        'Creator': ['XMP-dc:Creator','IPTC:By-line','PostScript:Creator','PDF:Author'],
        'Rights': ['XMP-dc:Rights','IPTC:CopyrightNotice','XMP-xmpRights:UsageTerms','PDF:Copyright'],
    }
    result = {}
    for field_name, names in aliases.items():
        for key in names:
            value = raw.get(key)
            if value:
                result['XMP-dc:'+field_name] = value
                break
    result['_found_fields'] = [k for k in aliases if result.get('XMP-dc:'+k)]
    result['_source'] = 'EPS metadata (XMP / IPTC / PostScript where available)'
    return result

def field(m, name):
    value = m.get('XMP-dc:'+name, '')
    if isinstance(value, list): return ', '.join(str(x) for x in value)
    if isinstance(value, dict): return str(value.get('x-default', next(iter(value.values()), '')))
    return str(value or '')

@app.get('/')
def home(): return render_template('index.html')

@app.post('/inspect')
def inspect():
    f=request.files.get('file')
    if not f: return jsonify(error='Вибери EPS'),400
    data=f.read()
    if not valid_eps(data): return jsonify(error='Це не схоже на EPS'),400
    with tempfile.TemporaryDirectory() as d:
        p=Path(d)/'input.eps'; p.write_bytes(data)
        return jsonify(metadata=meta(p), boundingBox=(bounds(data) or b'').decode('ascii','replace'))

@app.post('/process')
def process():
    files = request.files.getlist('files')
    if not files or len(files) > MAX_FILES:
        return jsonify(error='Оберіть від 1 до 20 EPS'), 400
    try:
        entries = json.loads(request.form.get('entries', '[]'))
    except (ValueError, TypeError):
        return jsonify(error='Некоректні дані окремих файлів'), 400
    if not isinstance(entries, list) or len(entries) != len(files):
        return jsonify(error='Кількість записів метаданих не збігається з кількістю EPS'), 400
    mode = request.form.get('mode', 'preserve')
    if mode not in ('update', 'preserve'):
        return jsonify(error='Некоректний режим'), 400
    out = io.BytesIO()
    rows, errors, used = [], [], set()
    with tempfile.TemporaryDirectory() as d, zipfile.ZipFile(out, 'w', zipfile.ZIP_DEFLATED) as z:
        for i, (f, item) in enumerate(zip(files, entries)):
            original = (f.filename or '').replace('\\', '/').split('/')[-1]
            if not isinstance(item, dict) or item.get('filename') != original:
                errors.append(f'Файл {i+1}: невідповідність назви'); continue
            if not original or original in ('.', '..') or original.casefold() in used:
                errors.append(f'{original}: некоректна або повторна назва'); continue
            used.add(original.casefold())
            raw = f.read()
            if not original.lower().endswith('.eps') or not valid_eps(raw):
                errors.append(f'{original}: це не EPS'); continue
            title = str(item.get('title') or '').strip()
            desc = str(item.get('description') or '').strip()
            author = str(item.get('author') or '').strip()
            rights = str(item.get('copyright') or '').strip()
            country = str(item.get('country') or '').strip()
            color = str(item.get('color') or '').strip()
            words = [w.strip() for w in re.split('[,\n]', str(item.get('keywords') or '')) if w.strip()]
            if (len(words)>50 or any(len(w)>150 for w in words) or len(title)>1000
                or len(desc)>5000 or len(author)>500 or len(rights)>1000
                or len(country)>150 or len(color)>150):
                errors.append(f'{original}: некоректна довжина поля або понад 50 keywords'); continue
            src=Path(d)/f'input_{i}.eps'
            dst=Path(d)/f'output_{i}.eps'
            src.write_bytes(raw)
            updated=raw
            if mode == 'update' and any([title,desc,words,author,rights]):
                args=['-overwrite_original','-P']
                if title: args+=['-XMP-dc:Title='+title]
                if desc: args+=['-XMP-dc:Description='+desc]
                if author: args+=['-XMP-dc:Creator='+author]
                if rights: args+=['-XMP-dc:Rights='+rights]
                if words:
                    args+=['-XMP-dc:Subject=']
                    args+=['-XMP-dc:Subject+='+w for w in words]
                args+=['-o',str(dst),str(src)]
                try: result=run(*args)
                except Exception as e:
                    errors.append(f'{original}: {e}'); continue
                if result.returncode or not dst.exists():
                    errors.append(f'{original}: {result.stderr.strip() or "помилка ExifTool"}'); continue
                updated=dst.read_bytes()
                if bounds(raw)!=bounds(updated):
                    errors.append(f'{original}: змінився BoundingBox'); continue
            # CSV values always come from this file's own editor fields.
            # In preserve mode the original EPS bytes are not modified.
            rows.append({'file name':original,'title':title,'description':desc,
                         'country':country,'color':color,'keywords':', '.join(words)})
            z.writestr('EPS/'+original,updated)
        stream=io.StringIO(newline='')
        writer=csv.DictWriter(stream,fieldnames=CSV_COLUMNS,lineterminator='\r\n')
        writer.writeheader()
        writer.writerows(rows)
        z.writestr('getty_esp_metadata.csv',stream.getvalue().encode('utf-8'))
        z.writestr('processing_notes.txt',
            'Getty ESP: one CSV row per EPS, with independent metadata.\n'
            'Original filenames are preserved. CSV columns match the supplied Getty template.\n'
            'Preserve mode does not modify EPS bytes. Update mode writes XMP using ExifTool.\n'
            'Processed: '+str(len(rows))+'; skipped: '+str(len(errors))+'\n'+'\n'.join(errors))
    if not rows:
        return jsonify(error='Жодного EPS не оброблено',details=errors),400
    out.seek(0)
    return send_file(out,mimetype='application/zip',as_attachment=True,
                     download_name='stock_metadata_individual_getty.zip')

@app.get('/health')
def health(): return jsonify(ok=True)
if __name__=='__main__': app.run(host='0.0.0.0',port=int(os.environ.get('PORT','10000')))
