from pathlib import Path
import pandas as pd


RAW_FILE = Path("data/raw/tiktok_apify_export.csv")
PROCESSED_DIR = Path("data/processed")
PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

OUTPUT_FILE = PROCESSED_DIR / "tiktok_public_metrics_clean.csv"
SUMMARY_FILE = PROCESSED_DIR / "tiktok_public_metrics_summary.csv"
TOP10_FILE = PROCESSED_DIR / "tiktok_top10_views.csv"


# 1. Cargar el CSV bruto
df = pd.read_csv(RAW_FILE)


# 2. Quedarnos solo con las columnas útiles
columns_to_keep = {
    "id": "video_id",
    "webVideoUrl": "video_url",
    "text": "caption",
    "createTimeISO": "posted_at",
    "playCount": "views",
    "diggCount": "likes",
    "commentCount": "comments",
    "shareCount": "shares",
    "collectCount": "saves",
    "isSlideshow": "is_slideshow",
    "videoMeta/duration": "duration_seconds",
    "musicMeta/musicName": "music_name",
    "musicMeta/musicAuthor": "music_author",
    "musicMeta/musicOriginal": "music_original",
    "textLanguage": "language",
}

df_clean = df[list(columns_to_keep.keys())].rename(columns=columns_to_keep)


# 3. Convertir fechas
df_clean["posted_at"] = pd.to_datetime(
    df_clean["posted_at"],
    errors="coerce",
    utc=True
)

df_clean["date"] = df_clean["posted_at"].dt.date
df_clean["year"] = df_clean["posted_at"].dt.year
df_clean["month"] = df_clean["posted_at"].dt.month
df_clean["day_of_week"] = df_clean["posted_at"].dt.day_name()
df_clean["hour"] = df_clean["posted_at"].dt.hour


# 4. Convertir métricas numéricas
numeric_columns = [
    "views",
    "likes",
    "comments",
    "shares",
    "saves",
    "duration_seconds",
]

for col in numeric_columns:
    df_clean[col] = pd.to_numeric(df_clean[col], errors="coerce").fillna(0).astype(int)


# 5. Limpiar texto
df_clean["caption"] = (
    df_clean["caption"]
    .fillna("")
    .astype(str)
    .str.strip()
)

df_clean["music_name"] = (
    df_clean["music_name"]
    .fillna("")
    .astype(str)
    .str.strip()
)

df_clean["music_author"] = (
    df_clean["music_author"]
    .fillna("")
    .astype(str)
    .str.strip()
)


# 6. Quitar duplicados
df_clean = df_clean.drop_duplicates(subset=["video_id"])


# 7. Crear métricas nuevas de rendimiento
df_clean["engagement_total"] = (
    df_clean["likes"]
    + df_clean["comments"]
    + df_clean["shares"]
    + df_clean["saves"]
)

df_clean["engagement_rate"] = df_clean["engagement_total"] / df_clean["views"]
df_clean["like_rate"] = df_clean["likes"] / df_clean["views"]
df_clean["comment_rate"] = df_clean["comments"] / df_clean["views"]
df_clean["share_rate"] = df_clean["shares"] / df_clean["views"]
df_clean["save_rate"] = df_clean["saves"] / df_clean["views"]

# Evitar infinitos o errores si algún vídeo tiene 0 views
rate_columns = [
    "engagement_rate",
    "like_rate",
    "comment_rate",
    "share_rate",
    "save_rate",
]

for col in rate_columns:
    df_clean[col] = df_clean[col].replace([float("inf"), -float("inf")], 0)
    df_clean[col] = df_clean[col].fillna(0)


# 8. Clasificar vídeos por tamaño
def classify_video(views):
    if views >= 1_000_000:
        return "viral"
    elif views >= 100_000:
        return "high"
    elif views >= 50_000:
        return "medium"
    else:
        return "low"


df_clean["performance_bucket"] = df_clean["views"].apply(classify_video)


# 9. Ordenar por fecha descendente
df_clean = df_clean.sort_values("posted_at", ascending=False)


# 10. Guardar CSV limpio
df_clean.to_csv(OUTPUT_FILE, index=False)


# 11. Crear resumen general
summary = pd.DataFrame([{
    "videos": len(df_clean),
    "total_views": df_clean["views"].sum(),
    "total_likes": df_clean["likes"].sum(),
    "total_comments": df_clean["comments"].sum(),
    "total_shares": df_clean["shares"].sum(),
    "total_saves": df_clean["saves"].sum(),
    "average_views": df_clean["views"].mean(),
    "median_views": df_clean["views"].median(),
    "max_views": df_clean["views"].max(),
    "average_engagement_rate": df_clean["engagement_rate"].mean(),
    "first_post_date": df_clean["posted_at"].min(),
    "last_post_date": df_clean["posted_at"].max(),
}])

summary.to_csv(SUMMARY_FILE, index=False)


# 12. Crear top 10 por visualizaciones
top10 = df_clean.sort_values("views", ascending=False).head(10)
top10.to_csv(TOP10_FILE, index=False)


print("Limpieza completada.")
print(f"Archivo limpio: {OUTPUT_FILE}")
print(f"Resumen: {SUMMARY_FILE}")
print(f"Top 10: {TOP10_FILE}")
print()
print(f"Vídeos procesados: {len(df_clean)}")
print(f"Visualizaciones totales: {df_clean['views'].sum():,}")
print(f"Vídeo más visto: {df_clean['views'].max():,} views")