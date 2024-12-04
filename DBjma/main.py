import flet as ft
import requests
import json
import sqlite3
from datetime import datetime
from contextlib import closing

def init_db():
    with closing(sqlite3.connect('weather.db')) as conn:
        with conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS areas (
                    id INTEGER PRIMARY KEY,
                    area_code TEXT NOT NULL UNIQUE,
                    area_name TEXT NOT NULL
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS forecasts (
                    id INTEGER PRIMARY KEY,
                    area_code TEXT NOT NULL,
                    publishing_office TEXT,
                    report_datetime TEXT,
                    weather TEXT,
                    FOREIGN KEY (area_code) REFERENCES areas(area_code)
                )
            """)

init_db()

def load_area_data_to_db(area_data):
    with closing(sqlite3.connect('weather.db')) as conn:
        with conn:
            for key, value in area_data["offices"].items():
                conn.execute("INSERT OR IGNORE INTO areas (area_code, area_name) VALUES (?, ?)",
                             (key, value["name"]))

# 地域データのロード
area_data = {}
try:
    with open('jma/areas.json', 'r', encoding='utf-8') as f:
        content = f.read()
        if content.strip() == "":
            raise json.JSONDecodeError("Empty file", content, 0)
        area_data = json.loads(content)
        load_area_data_to_db(area_data)
except FileNotFoundError:
    print("Error: 'jma/areas.json' ファイルが見つかりません")
except json.JSONDecodeError as e:
    print(f"JSONDecodeError: {e} - JSON Content: {content}")
except Exception as e:
    print(f"Unexpected error: {e}")

def main(page: ft.Page):
    page.scroll = ft.ScrollMode.AUTO

    if not area_data:
        output = ft.Text("地域データの読み込みに失敗しました。")
        page.controls.append(output)
        page.update()
        return

    # 地域データを地方→県の構造で整理
    regions = {}
    for key, value in area_data["centers"].items():
        region_name = value["name"]
        regions[region_name] = {}

    for key, value in area_data["offices"].items():
        parent_center = value["parent"]
        if parent_center in area_data["centers"]:
            region_name = area_data["centers"][parent_center]["name"]
            regions[region_name][key] = value["name"]

    # ドロップダウンの初期化
    region_dropdown = ft.Dropdown(
        label="地方を選択してください：",
        options=[ft.dropdown.Option(region) for region in regions.keys()],
        width=300,
        on_change=lambda e: update_office_dropdown(e.control.value)
    )

    office_dropdown = ft.Dropdown(
        label="県を選択してください：",
        options=[],
        width=300,
        on_change=lambda e: get_forecast(e.control.value)
    )

    output = ft.Text()
    
    def update_office_dropdown(selected_region):
        if selected_region:
            office_dropdown.options = [
                ft.dropdown.Option(key, name)
                for key, name in regions[selected_region].items()
            ]
            office_dropdown.value = None
        else:
            office_dropdown.options = []
        office_dropdown.update()

    def get_forecast(area_code):
        if area_code:
            response = requests.get(f'https://www.jma.go.jp/bosai/forecast/data/forecast/{area_code}.json')
            if response.status_code == 200:
                forecast_data = response.json()
                save_forecast_to_db(area_code, forecast_data)
                display_forecast(area_code)
            else:
                output.value = f"Error: {response.status_code}"
                page.update()

    def save_forecast_to_db(area_code, forecast_data):
        with closing(sqlite3.connect('weather.db')) as conn:
            with conn:
                for entry in forecast_data:
                    publishing_office = entry.get("publishingOffice", "不明")
                    report_datetime = entry.get("reportDatetime", "不明")
                    for time_series in entry.get("timeSeries", []):
                        for area in time_series.get("areas", []):
                            weather = area.get("weathers", ["情報なし"])[0]
                            conn.execute("""
                                INSERT INTO forecasts (area_code, publishing_office, report_datetime, weather)
                                VALUES (?, ?, ?, ?)
                            """, (area_code, publishing_office, report_datetime, weather))

    def get_forecast_from_db(area_code):
        with closing(sqlite3.connect('weather.db')) as conn:
            with conn:
                cursor = conn.execute("""
                    SELECT publishing_office, report_datetime, weather FROM forecasts
                    WHERE area_code = ?
                    ORDER BY report_datetime DESC
                """, (area_code,))
                return cursor.fetchall()

    def display_forecast(area_code):
        forecasts = get_forecast_from_db(area_code)
        page.controls.clear()
        page.controls.append(ft.Row([back_button]))
        for publishing_office, report_datetime, weather in forecasts:
            title = ft.Text(f"{publishing_office} {report_datetime}", style=ft.TextStyle(size=24, weight="bold"))
            page.controls.append(title)
            weather_text = ft.Text(f"天気: {weather}")
            page.controls.append(weather_text)
        page.update()

    def show_area_selection(e=None):
        page.controls.clear()
        page.controls.append(ft.Column([region_dropdown, office_dropdown, output]))
        page.update()

    # 「戻る」ボタン
    back_button = ft.ElevatedButton(text="戻る", on_click=show_area_selection)

    # 地域選択画面を初期表示
    show_area_selection()

ft.app(target=main)