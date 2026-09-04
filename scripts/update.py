import re
import urllib.request
import urllib.error
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

SOURCE_URL = "https://iptv-org.github.io/iptv/countries/br.m3u"
OUTPUT_FILE = Path("brasil.m3u")

TIMEOUT = 8
MAX_WORKERS = 20

translations = {
    "Sports": "Esportes",
    "News": "Notícias",
    "Movies": "Filmes",
    "Series": "Séries",
    "Entertainment": "Entretenimento",
    "General": "Geral",
    "Kids": "Infantil",
    "Education": "Educação",
    "Religious": "Religioso",
    "Legislative": "Legislativo",
    "Culture": "Cultura",
    "Outdoor": "Ar Livre",
    "Shop": "Compras",
    "Undefined": "Outros",
    "Classic": "Clássicos",
    "Lifestyle": "Estilo de Vida",
    "Business": "Negócios",
    "Cooking": "Culinária",
    "Documentary": "Documentários",
    "Family": "Família",
    "Music": "Música",
    "Public": "Público",
    "Relax": "Relaxamento",
    "Science": "Ciência",
    "Travel": "Viagens",
    "Weather": "Clima",
    "Animation": "Animação",
    "Auto": "Automóveis",
}


def download_playlist():
    print("Baixando lista do Brasil...")

    request = urllib.request.Request(
        SOURCE_URL,
        headers={"User-Agent": "Mozilla/5.0"}
    )

    with urllib.request.urlopen(request, timeout=30) as response:
        return response.read().decode("utf-8", errors="ignore")


def translate_categories(text):
    def replace(match):
        original = match.group(1)

        categories = [
            c.strip()
            for c in original.split(";")
            if c.strip()
        ]

        translated = [
            translations.get(c, c)
            for c in categories
        ]

        return 'group-title="' + ";".join(translated) + '"'

    return re.sub(
        r'group-title="([^"]*)"',
        replace,
        text
    )


def parse_playlist(text):
    lines = text.splitlines()

    channels = []
    current_info = None

    for line in lines:
        line = line.strip()

        if line.startswith("#EXTINF"):
            current_info = line

        elif line and not line.startswith("#") and current_info:
            channels.append({
                "info": current_info,
                "url": line
            })

            current_info = None

    return channels


def normalize_url(url):
    return url.strip().rstrip("/")


def remove_duplicates(channels):
    seen_urls = set()
    unique = []

    for channel in channels:
        key = normalize_url(channel["url"])

        if key in seen_urls:
            continue

        seen_urls.add(key)
        unique.append(channel)

    return unique


def stream_works(url):
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept": "*/*",
    }

    request = urllib.request.Request(
        url,
        headers=headers,
        method="GET"
    )

    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
            status = response.getcode()

            if 200 <= status < 400:
                return True

    except Exception:
        return False

    return False


def test_channels(channels):
    working = []

    print(f"Testando {len(channels)} canais...")

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {
            executor.submit(stream_works, channel["url"]): channel
            for channel in channels
        }

        total = len(futures)
        done = 0

        for future in as_completed(futures):
            channel = futures[future]
            done += 1

            try:
                ok = future.result()
            except Exception:
                ok = False

            if ok:
                working.append(channel)

            print(
                f"[{done}/{total}] "
                f"{'OK' if ok else 'OFF'} "
                f"{channel['url'][:80]}"
            )

    return working


def generate_playlist(channels):
    lines = ["#EXTM3U"]

    for channel in channels:
        lines.append(channel["info"])
        lines.append(channel["url"])

    return "\n".join(lines) + "\n"


def main():
    raw = download_playlist()

    translated = translate_categories(raw)

    channels = parse_playlist(translated)

    print(f"Encontrados: {len(channels)}")

    channels = remove_duplicates(channels)

    print(f"Após remover duplicados: {len(channels)}")

    working = test_channels(channels)

    print(f"Funcionando: {len(working)}")

    output = generate_playlist(working)

    OUTPUT_FILE.write_text(
        output,
        encoding="utf-8"
    )

    print(f"Arquivo salvo: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
