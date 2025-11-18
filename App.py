import os
import psycopg2
from flask import Flask, render_template_string, request

app = Flask(__name__)

DATABASE_URL = os.environ.get("DATABASE_URL")

TEMPLATE = """
<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <title>Video Index</title>
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <style>
    body { font-family: -apple-system, BlinkMacSystemFont, sans-serif; max-width: 900px; margin: 10px auto; padding: 0 10px; }
    table { border-collapse: collapse; width: 100%; font-size: 14px; }
    th, td { border: 1px solid #ccc; padding: 6px 8px; word-break: break-all; }
    th { background: #eee; }
    form { margin-bottom: 10px; }
    @media (max-width: 600px) {
      table, thead, tbody, th, td, tr { display: block; }
      th { display: none; }
      tr { margin-bottom: 8px; border: 1px solid #ccc; }
      td { border: none; border-bottom: 1px solid #ddd; }
      td:nth-child(1)::before { content: "Title: "; font-weight: bold; }
      td:nth-child(2)::before { content: "Page: "; font-weight: bold; }
      td:nth-child(3)::before { content: "MP4: "; font-weight: bold; }
    }
  </style>
</head>
<body>
  <h1>Video Index</h1>
  <form method="get">
    <input type="text" name="q" placeholder="Search" value="{{ q|e }}">
    <button type="submit">Search</button>
  </form>
  <p>Showing {{ videos|length }} result(s).</p>
  <table>
    <thead>
      <tr>
        <th>Title</th>
        <th>Page</th>
        <th>Video (MP4)</th>
      </tr>
    </thead>
    <tbody>
    {% for v in videos %}
      <tr>
        <td>{{ v[0] }}</td>
        <td><a href="{{ v[1] }}" target="_blank">Open page</a></td>
        <td><a href="{{ v[2] }}" target="_blank">Open MP4</a></td>
      </tr>
    {% endfor %}
    </tbody>
  </table>
</body>
</html>
"""

def get_conn():
    if not DATABASE_URL:
        raise RuntimeError("DATABASE_URL not set")
    return psycopg2.connect(DATABASE_URL)

@app.route("/")
def index():
    q = request.args.get("q", "").strip()
    conn = get_conn()
    cur = conn.cursor()
    if q:
        cur.execute(
            """
            SELECT title, page_url, mp4_url
            FROM videos
            WHERE title ILIKE %s OR page_url ILIKE %s OR mp4_url ILIKE %s
            ORDER BY id DESC
            LIMIT 500
            """,
            (f"%{q}%", f"%{q}%", f"%{q}%",),
        )
    else:
        cur.execute(
            """
            SELECT title, page_url, mp4_url
            FROM videos
            ORDER BY id DESC
            LIMIT 200
            """
        )
    videos = cur.fetchall()
    conn.close()
    return render_template_string(TEMPLATE, videos=videos, q=q)

if __name__ == "__main__":
    app.run(debug=True)
