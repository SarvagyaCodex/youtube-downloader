import os
import platform
from pathlib import Path

from flask import Flask, render_template_string, request, send_file
import yt_dlp

app = Flask(__name__)


# ============================================================
# DOWNLOAD DIRECTORY
# ============================================================

def get_default_download_folder():
    """
    Automatically choose a sensible Downloads folder.

    Windows:
        C:\\Users\\Username\\Downloads

    Android / Termux:
        /storage/emulated/0/Download

    Linux/macOS:
        ~/Downloads
    """

    system = platform.system().lower()

    # Android / Termux
    if "android" in system:
        android_download = Path("/storage/emulated/0/Download")

        if android_download.exists():
            return str(android_download)

        return str(Path.home() / "Downloads")

    # Windows
    if system == "windows":
        downloads = Path.home() / "Downloads"

        if downloads.exists():
            return str(downloads)

        return str(Path.home())

    # Linux / macOS
    downloads = Path.home() / "Downloads"

    if downloads.exists():
        return str(downloads)

    return str(Path.home())


DEFAULT_DOWNLOAD_FOLDER = get_default_download_folder()


# ============================================================
# FLASK APP
# ============================================================

app = Flask(__name__)


# ============================================================
# HTML
# ============================================================

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">

<head>

    <meta charset="UTF-8">

    <meta
        name="viewport"
        content="width=device-width, initial-scale=1.0"
    >

    <title>YouTube Video Downloader</title>

    <!-- Tailwind -->
    <script src="https://cdn.tailwindcss.com"></script>

    <!-- Material Icons -->
    <link
        href="https://fonts.googleapis.com/icon?family=Material+Icons"
        rel="stylesheet"
    >

    <style>

        * {
            box-sizing: border-box;
        }

        body {
            margin: 0;
            min-height: 100vh;
            font-family: Arial, sans-serif;
            background:
                radial-gradient(
                    circle at top,
                    #172554 0%,
                    #0f172a 35%,
                    #020617 100%
                );
            color: white;
        }

        .glass {
            background: rgba(15, 23, 42, 0.78);
            border: 1px solid rgba(255, 255, 255, 0.10);
            backdrop-filter: blur(18px);
            -webkit-backdrop-filter: blur(18px);
        }

        .card {
            animation: slideIn 0.45s ease;
        }

        .format-card {
            transition:
                transform 0.18s ease,
                background 0.18s ease,
                border-color 0.18s ease;
        }

        .format-card:hover {
            transform: translateY(-2px);
            background: rgba(30, 41, 59, 0.95);
            border-color: rgba(96, 165, 250, 0.45);
        }

        .btn {
            transition:
                transform 0.15s ease,
                opacity 0.15s ease;
        }

        .btn:active {
            transform: scale(0.97);
        }

        .btn:hover {
            opacity: 0.92;
        }

        .loader {
            width: 20px;
            height: 20px;
            border: 3px solid rgba(255,255,255,0.3);
            border-top-color: white;
            border-radius: 50%;
            animation: spin 0.8s linear infinite;
        }

        @keyframes spin {
            to {
                transform: rotate(360deg);
            }
        }

        @keyframes slideIn {
            from {
                opacity: 0;
                transform: translateY(15px);
            }

            to {
                opacity: 1;
                transform: translateY(0);
            }
        }

        input::placeholder {
            color: #64748b;
        }

        input {
            color: white;
        }

    </style>

</head>


<body class="flex items-center justify-center p-4">

<div class="w-full max-w-2xl">

    <!-- Main Card -->

    <div class="glass rounded-3xl shadow-2xl p-6 md:p-8 card">

        <!-- Header -->

        <div class="text-center mb-8">

            <div
                class="mx-auto mb-4 flex items-center justify-center
                       w-16 h-16 rounded-2xl
                       bg-blue-500/15"
            >

                <span
                    class="material-icons text-blue-400"
                    style="font-size:42px;"
                >
                    cloud_download
                </span>

            </div>

            <h1 class="text-3xl md:text-4xl font-bold">
                YouTube Downloader
            </h1>

            <p class="text-slate-400 mt-2">
                Simple local video downloader
            </p>

        </div>


        <!-- Error -->

        {% if error %}

        <div
            class="mb-6 p-4 rounded-xl
                   bg-red-500/10
                   border border-red-500/30
                   text-red-300"
        >

            <div class="flex items-start gap-3">

                <span class="material-icons">
                    error_outline
                </span>

                <div>
                    <p class="font-semibold">
                        Something went wrong
                    </p>

                    <p class="text-sm mt-1">
                        {{ error }}
                    </p>
                </div>

            </div>

        </div>

        {% endif %}


        <!-- URL Form -->

        <form
            action="/"
            method="post"
            class="space-y-5"
            onsubmit="showLoading()"
        >

            <!-- URL -->

            <div>

                <label class="block text-sm text-slate-300 mb-2">
                    Video URL
                </label>

                <div
                    class="flex items-center gap-3
                           bg-slate-900/70
                           border border-slate-700
                           rounded-xl
                           px-4 py-3
                           focus-within:border-blue-500"
                >

                    <span class="material-icons text-slate-400">
                        link
                    </span>

                    <input
                        type="url"
                        name="video_url"
                        value="{{ video_url or '' }}"
                        placeholder="Paste video URL here..."
                        required
                        class="w-full bg-transparent outline-none"
                    >

                </div>

            </div>


            <!-- Save Location -->

            <div>

                <label class="block text-sm text-slate-300 mb-2">
                    Save Location
                </label>

                <div
                    class="flex items-center gap-3
                           bg-slate-900/70
                           border border-slate-700
                           rounded-xl
                           px-4 py-3
                           focus-within:border-blue-500"
                >

                    <span class="material-icons text-slate-400">
                        folder
                    </span>

                    <input
                        type="text"
                        name="save_path"
                        value="{{ save_path or default_path }}"
                        required
                        class="w-full bg-transparent outline-none"
                    >

                </div>

                <p class="text-xs text-slate-500 mt-2">
                    Default: your system Downloads folder
                </p>

            </div>


            <!-- Fetch Button -->

            <button
                id="fetchButton"
                type="submit"
                class="btn w-full
                       bg-blue-600
                       hover:bg-blue-500
                       rounded-xl
                       py-3.5
                       font-semibold
                       flex items-center justify-center gap-2"
            >

                <span
                    id="fetchIcon"
                    class="material-icons"
                >
                    search
                </span>

                <span id="fetchText">
                    Fetch Formats
                </span>

            </button>

        </form>


        <!-- Formats -->

        {% if formats %}

        <div class="mt-8">

            <div class="flex items-center justify-between mb-4">

                <div>

                    <h2 class="text-xl font-bold">
                        Available Formats
                    </h2>

                    {% if video_title %}

                    <p class="text-sm text-slate-400 mt-1">
                        {{ video_title }}
                    </p>

                    {% endif %}

                </div>

                <span
                    class="text-xs
                           px-3 py-1
                           rounded-full
                           bg-blue-500/10
                           text-blue-300"
                >
                    {{ formats|length }} formats
                </span>

            </div>


            <form
                action="/download"
                method="post"
                onsubmit="showDownloadLoading()"
            >

                <input
                    type="hidden"
                    name="video_url"
                    value="{{ video_url }}"
                >

                <input
                    type="hidden"
                    name="save_path"
                    value="{{ save_path }}"
                >


                <div class="space-y-3 max-h-96 overflow-y-auto pr-1">

                    {% for f in formats %}

                    <label
                        class="format-card
                               block
                               cursor-pointer
                               bg-slate-900/60
                               border border-slate-700
                               rounded-xl
                               p-4"
                    >

                        <div class="flex items-center gap-3">

                            <input
                                type="radio"
                                name="format_id"
                                value="{{ f.format_id }}"
                                required
                                class="w-4 h-4"
                            >

                            <div class="flex-1">

                                <div class="flex items-center gap-2 flex-wrap">

                                    <span class="font-semibold text-white">
                                        {{ f.quality }}
                                    </span>

                                    {% if f.ext %}

                                    <span
                                        class="text-xs
                                               px-2 py-1
                                               rounded-md
                                               bg-slate-800
                                               text-slate-300"
                                    >
                                        {{ f.ext }}
                                    </span>

                                    {% endif %}

                                    {% if f.has_audio %}

                                    <span
                                        class="text-xs
                                               px-2 py-1
                                               rounded-md
                                               bg-green-500/10
                                               text-green-300"
                                    >
                                        Audio
                                    </span>

                                    {% else %}

                                    <span
                                        class="text-xs
                                               px-2 py-1
                                               rounded-md
                                               bg-yellow-500/10
                                               text-yellow-300"
                                    >
                                        Video only
                                    </span>

                                    {% endif %}

                                </div>


                                <p class="text-xs text-slate-500 mt-1">

                                    Format {{ f.format_id }}

                                    {% if f.filesize %}
                                    • {{ f.filesize }}
                                    {% endif %}

                                    {% if f.fps %}
                                    • {{ f.fps }} FPS
                                    {% endif %}

                                </p>

                            </div>

                        </div>

                    </label>

                    {% endfor %}

                </div>


                <!-- Download -->

                <button
                    id="downloadButton"
                    type="submit"
                    class="btn
                           w-full
                           mt-5
                           bg-green-600
                           hover:bg-green-500
                           rounded-xl
                           py-3.5
                           font-semibold
                           flex items-center justify-center gap-2"
                >

                    <span
                        id="downloadIcon"
                        class="material-icons"
                    >
                        download
                    </span>

                    <span id="downloadText">
                        Download Video
                    </span>

                </button>

            </form>

        </div>

        {% endif %}


        <!-- Footer -->

        <div class="mt-8 pt-5 border-t border-slate-800 text-center">

            <p class="text-xs text-slate-500">
                Runs locally on your computer or supported Android
                Python environment.
            </p>

        </div>

    </div>

</div>


<script>

function showLoading() {

    const button = document.getElementById("fetchButton");

    const icon = document.getElementById("fetchIcon");

    const text = document.getElementById("fetchText");

    if (button) {

        button.disabled = true;

        icon.innerHTML = "";

        icon.className = "loader";

        text.innerText = "Fetching formats...";

    }

}


function showDownloadLoading() {

    const button = document.getElementById("downloadButton");

    const icon = document.getElementById("downloadIcon");

    const text = document.getElementById("downloadText");

    if (button) {

        button.disabled = true;

        icon.innerHTML = "";

        icon.className = "loader";

        text.innerText = "Downloading...";

    }

}

</script>

</body>

</html>
"""


# ============================================================
# FORMAT HELPERS
# ============================================================

def format_filesize(size):
    """Convert bytes into a readable size."""

    if not size:
        return ""

    try:
        size = float(size)

        units = ["B", "KB", "MB", "GB", "TB"]

        for unit in units:

            if size < 1024:
                return f"{size:.1f} {unit}"

            size /= 1024

        return f"{size:.1f} PB"

    except Exception:
        return ""


def prepare_formats(raw_formats):
    """
    Convert yt-dlp formats into simpler objects for the UI.
    """

    result = []

    for f in raw_formats:

        format_id = f.get("format_id")

        if not format_id:
            continue

        # Ignore formats that aren't useful media formats.
        if f.get("vcodec") == "none" and f.get("acodec") == "none":
            continue

        height = f.get("height")

        if height:
            quality = f"{height}p"
        elif f.get("abr"):
            quality = f"{round(f['abr'])} kbps"
        else:
            quality = f.get("format_note") or "Unknown quality"

        has_audio = f.get("acodec") not in (None, "none")

        filesize = (
            f.get("filesize")
            or f.get("filesize_approx")
        )

        result.append({
            "format_id": format_id,
            "ext": f.get("ext", ""),
            "quality": quality,
            "has_audio": has_audio,
            "filesize": format_filesize(filesize),
            "fps": f.get("fps")
        })

    # Highest quality first.
    def sort_key(item):
        try:
            quality = item["quality"].replace("p", "")
            return float(quality)
        except Exception:
            return 0

    result.sort(
        key=sort_key,
        reverse=True
    )

    return result


# ============================================================
# HOME ROUTE
# ============================================================

@app.route("/", methods=["GET", "POST"])
def index():

    formats = None
    video_url = ""
    save_path = DEFAULT_DOWNLOAD_FOLDER
    video_title = ""
    error = None

    if request.method == "POST":

        video_url = request.form.get(
            "video_url",
            ""
        ).strip()

        save_path = request.form.get(
            "save_path",
            DEFAULT_DOWNLOAD_FOLDER
        ).strip()

        if not video_url:

            error = "Please enter a video URL."

            return render_template_string(
                HTML_TEMPLATE,
                formats=formats,
                video_url=video_url,
                save_path=save_path,
                default_path=DEFAULT_DOWNLOAD_FOLDER,
                video_title=video_title,
                error=error
            )

        try:

            ydl_opts = {
                "quiet": True,
                "no_warnings": True,
                "skip_download": True
            }

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:

                info = ydl.extract_info(
                    video_url,
                    download=False
                )

            raw_formats = info.get(
                "formats",
                []
            )

            formats = prepare_formats(
                raw_formats
            )

            video_title = info.get(
                "title",
                ""
            )

            if not formats:

                error = (
                    "No downloadable formats were found "
                    "for this video."
                )

        except Exception as e:

            error = str(e)

    return render_template_string(
        HTML_TEMPLATE,
        formats=formats,
        video_url=video_url,
        save_path=save_path,
        default_path=DEFAULT_DOWNLOAD_FOLDER,
        video_title=video_title,
        error=error
    )


# ============================================================
# DOWNLOAD ROUTE
# ============================================================

@app.route("/download", methods=["POST"])
def download():

    video_url = request.form.get(
        "video_url",
        ""
    ).strip()

    save_path = request.form.get(
        "save_path",
        DEFAULT_DOWNLOAD_FOLDER
    ).strip()

    format_id = request.form.get(
        "format_id",
        ""
    ).strip()

    if not video_url:

        return "Error: Video URL is missing.", 400

    if not format_id:

        return "Error: Please select a format.", 400

    if not save_path:

        save_path = DEFAULT_DOWNLOAD_FOLDER

    try:

        # Create the folder if necessary.
        os.makedirs(
            save_path,
            exist_ok=True
        )

    except Exception as e:

        return (
            f"Error creating download folder: {e}"
        ), 500


    try:

        # ----------------------------------------------------
        # Download options
        # ----------------------------------------------------

        ydl_opts = {

            # Selected format.
            #
            # If the selected format is video-only, yt-dlp
            # may download only that stream.
            "format": format_id,

            # Output filename.
            "outtmpl": os.path.join(
                save_path,
                "%(title)s.%(ext)s"
            ),

            # Keep console output quiet.
            "quiet": True,

            "no_warnings": True,

            # Let yt-dlp use its normal filename handling.
            "restrictfilenames": False,

            # Do not overwrite an existing file.
            "overwrites": False
        }


        with yt_dlp.YoutubeDL(ydl_opts) as ydl:

            info = ydl.extract_info(
                video_url,
                download=True
            )

            video_file = ydl.prepare_filename(
                info
            )


        # ----------------------------------------------------
        # Check downloaded file
        # ----------------------------------------------------

        if not os.path.exists(video_file):

            return (
                "Download finished, but the output file "
                "could not be located."
            ), 500


        return send_file(
            video_file,
            as_attachment=True
        )


    except Exception as e:

        return (
            "<h2>Download failed</h2>"
            f"<p>{e}</p>"
            "<p><a href='/'>Go back</a></p>"
        ), 500


# ============================================================
# START SERVER
# ============================================================

if __name__ == "__main__":

    print()
    print("=" * 55)
    print("       YouTube Video Downloader")
    print("=" * 55)
    print()
    print("Operating system:", platform.system())
    print("Download folder:", DEFAULT_DOWNLOAD_FOLDER)
    print()
    print("Open this address in your browser:")
    print("http://127.0.0.1:5000")
    print()
    print("Press CTRL+C to stop the server.")
    print("=" * 55)
    print()

    app.run(
        host="127.0.0.1",
        port=5000,
        debug=False
    )
