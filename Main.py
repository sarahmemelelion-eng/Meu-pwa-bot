import io, zipfile, os, threading
from PIL import Image, ImageDraw
from flask import Flask
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# Mantém o Render acordado
app_web = Flask(__name__)
@app_web.route('/')
def home():
    return "Bot ligado!"
threading.Thread(target=lambda: app_web.run(host='0.0.0.0', port=10000)).start()

MANIFEST = """{
  "name": "Meu App",
  "short_name": "Meu App",
  "start_url": "/",
  "scope": "/",
  "display": "standalone",
  "background_color": "#0a0a0a",
  "theme_color": "#000000",
  "icons": [
    {"src": "icon-192.png", "sizes": "192x192", "type": "image/png", "purpose": "any"},
    {"src": "icon-512.png", "sizes": "512x512", "type": "image/png", "purpose": "any"}
  ]
}
"""

SW = """self.addEventListener('install', e => { self.skipWaiting(); });
self.addEventListener('activate', e => { self.clients.claim(); });
self.addEventListener('fetch', e => { e.respondWith(fetch(e.request).catch(() => caches.match(e.request))); });
"""

def criar_icone(size):
    img = Image.new('RGB', (size, size), (255, 107, 157))
    draw = ImageDraw.Draw(img)
    draw.rounded_rectangle([size*0.2, size*0.2, size*0.8, size*0.8], radius=size*0.1, fill=(255,255,255))
    draw.rectangle([size*0.48, size*0.2, size*0.52, size*0.8], fill=(255,107,157))
    for i in range(3):
        y = size*0.35 + i*size*0.12
        draw.line([size*0.3, y, size*0.7, y], fill=(255,107,157), width=int(size*0.03))
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    buf.seek(0)
    return buf.read()

def arrumar_html(html_texto):
    if 'manifest.json' not in html_texto:
        html_texto = html_texto.replace('</head>', '<link rel="manifest" href="manifest.json">\n</head>')
    if 'serviceWorker' not in html_texto:
        script = "<script>if('serviceWorker' in navigator){navigator.serviceWorker.register('sw.js');}</script>\n</body>"
        if '</body>' in html_texto:
            html_texto = html_texto.replace('</body>', script)
        else:
            html_texto += script
    return html_texto

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Oi! 👋 Manda seu arquivo .html aqui que eu te devolvo um .zip já pronto pra virar PWA!")

async def receber_html(update: Update, context: ContextTypes.DEFAULT_TYPE):
    doc = update.message.document
    if not doc.file_name.endswith('.html'):
        await update.message.reply_text("Manda um arquivo .html, tá? 😅")
        return
    await update.message.reply_text("Recebi! Gerando seu PWA... ⏳")
    arquivo = await doc.get_file()
    buf_html = io.BytesIO()
    await arquivo.download_to_memory(buf_html)
    html_original = buf_html.getvalue().decode('utf-8', errors='ignore')
    html_pronto = arrumar_html(html_original)
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as z:
        z.writestr('index.html', html_pronto)
        z.writestr('manifest.json', MANIFEST)
        z.writestr('sw.js', SW)
        z.writestr('icon-192.png', criar_icone(192))
        z.writestr('icon-512.png', criar_icone(512))
    zip_buffer.seek(0)
    await update.message.reply_document(document=zip_buffer, filename='meu-app-pwa.zip', caption="Prontinho! 🎉\n1. Baixa esse zip\n2. Arrasta no Netlify Drop\n3. Abre o link no Chrome > 3 pontinhos > Instalar app")

def main():
    token = os.environ.get("BOT_TOKEN")
    app = Application.builder().token(token).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.Document.ALL, receber_html))
    print("Bot ligado!")
    app.run_polling()

if __name__ == '__main__':
    main()
