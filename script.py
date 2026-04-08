import yt_dlp

def buscar_y_descargar():
    termino = input("Ingrese término de búsqueda: ")
    
    ydl_opts_busqueda = {
        'format': 'bestvideo[height<=720]+bestaudio[abr<=128]/best[height<=720]',
        'quiet': True,
        'no_warnings': True,
        'extract_flat': True,
    }

    with yt_dlp.YoutubeDL(ydl_opts_busqueda) as ydl:
        # Busca 9 resultados
        resultado = ydl.extract_info(f"ytsearch9:{termino}", download=False)
        
        if 'entries' not in resultado or not resultado['entries']:
            print("No se encontraron resultados.")
            return

        videos = resultado['entries']
        
        print("\n--- RESULTADOS ENCONTRADOS ---")
        for i, video in enumerate(videos, 1):
            titulo = video.get('title', 'Sin título')
            descripcion = video.get('description', 'Sin descripción')
            # Acortar descripción para legibilidad en consola
            desc_corta = (descripcion[:150] + '...') if descripcion else "N/A"
            print(f"[{i}] {titulo}")
            print(f"    SINOPSIS: {desc_corta}\n")

    try:
        seleccion = int(input("Seleccione el número del video a descargar (1-9): "))
        if not (1 <= seleccion <= len(videos)):
            print("Selección fuera de rango.")
            return
    except ValueError:
        print("Entrada no válida.")
        return

    video_seleccionado = videos[seleccion - 1]
    url_video = video_seleccionado['url']

    ydl_opts_descarga = {
        'format': 'bestvideo[height<=720]+bestaudio[abr<=128]/best[height<=720]',
        'outtmpl': '%(title)s.%(ext)s',
        'merge_output_format': 'mp4',
        'postprocessors': [{
            'key': 'FFmpegVideoConvertor',
            'preferedformat': 'mp4',
        }],
    }

    print(f"\nDescargando: {video_seleccionado.get('title')}...")
    with yt_dlp.YoutubeDL(ydl_opts_descarga) as ydl:
        ydl.download([url_video])

if __name__ == "__main__":
    buscar_y_descargar()
