import os, re, io, zipfile, tempfile, subprocess, json
from pathlib import Path
from flask import Flask, request, send_file, render_template, jsonify

app=Flask(__name__)
app.config['MAX_CONTENT_LENGTH']=60*1024*1024
MAX_FILES=20

def run(*args):
    return subprocess.run(['exiftool',*args],capture_output=True,text=True,timeout=35)

def valid_eps(data):
    return data.startswith(b'%!PS-Adobe') or data.startswith(b'\xc5\xd0\xd3\xc6')

def bounds(data):
    # Inspect original PostScript header only; EPS binary previews may precede it
    pos=data.find(b'%!PS-Adobe')
    if pos<0:return None
    header=data[pos:pos+8192]
    match=re.search(rb'(?m)^%%BoundingBox:\s*([^\r\n]+)',header)
    return match.group(1) if match else None

def meta(path):
    p=run('-j','-G1','-a','-s','-XMP-dc:Title','-XMP-dc:Description','-XMP-dc:Subject',str(path))
    if p.returncode:return {'error':p.stderr.strip() or 'ExifTool failed'}
    try:return json.loads(p.stdout)[0]
    except Exception:return {'error':'Could not parse metadata'}

@app.get('/')
def home():return render_template('index.html')

@app.post('/inspect')
def inspect():
    f=request.files.get('file')
    if not f:return jsonify(error='Вибери EPS'),400
    data=f.read()
    if not valid_eps(data):return jsonify(error='Це не схоже на EPS'),400
    with tempfile.TemporaryDirectory() as d:
        p=Path(d)/'input.eps';p.write_bytes(data)
        return jsonify(metadata=meta(p),boundingBox=(bounds(data) or b'').decode('ascii','replace'))

@app.post('/process')
def process():
    files=request.files.getlist('files')
    if not files or len(files)>MAX_FILES:return jsonify(error='Потрібно 1–20 EPS'),400
    title=request.form.get('title','').strip(); desc=request.form.get('description','').strip()
    words=[w.strip() for w in request.form.get('keywords','').replace('\n',',').split(',') if w.strip()]
    if len(words)>50:return jsonify(error='Максимум 50 ключових слів'),400
    if any(len(w)>150 for w in words) or len(title)>1000 or len(desc)>5000:return jsonify(error='Занадто довге поле'),400
    if not any([title,desc,words]):return jsonify(error='Заповни хоча б одне поле'),400
    out=io.BytesIO(); errors=[]
    with tempfile.TemporaryDirectory() as d,zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED) as z:
        for i,f in enumerate(files):
            raw=f.read()
            if not f.filename.lower().endswith('.eps') or not valid_eps(raw):
                errors.append(f'{f.filename}: не EPS');continue
            src=Path(d)/f'input_{i}.eps';dst=Path(d)/f'output_{i}.eps';src.write_bytes(raw)
            args=['-overwrite_original','-P']
            if title:args+=['-XMP-dc:Title='+title]
            if desc:args+=['-XMP-dc:Description='+desc]
            if words:
                args+=['-XMP-dc:Subject=']
                args+=['-XMP-dc:Subject+='+w for w in words]
            args+=['-o',str(dst),str(src)]
            result=run(*args)
            if result.returncode or not dst.exists():
                errors.append(f'{f.filename}: {result.stderr.strip() or "помилка ExifTool"}');continue
            updated=dst.read_bytes()
            if bounds(raw)!=bounds(updated):
                errors.append(f'{f.filename}: BoundingBox змінився, файл не видано');continue
            actual=meta(dst)
            if 'error' in actual:
                errors.append(f'{f.filename}: перевірка метаданих не вдалася');continue
            name=Path(f.filename).stem
            z.writestr(f'{i+1:02d}_{name}_metadata.eps',updated)
            z.writestr(f'{i+1:02d}_{name}_verification.json',json.dumps(actual,ensure_ascii=False,indent=2))
        z.writestr('processing_notes.txt','ExifTool XMP verification included for each EPS. Stock platform import is not guaranteed.\n'+ '\n'.join(errors))
    out.seek(0)
    return send_file(out,mimetype='application/zip',as_attachment=True,download_name='stock_metadata_eps.zip')

@app.get('/health')
def health():return jsonify(ok=True)

if __name__=='__main__':app.run(host='0.0.0.0',port=int(os.environ.get('PORT','10000')))
