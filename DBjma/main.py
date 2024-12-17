import flet as ft
import requests
import json
import sqlite3
from datetime import datetime

# SQLiteデータベースの初期化
conn = sqlite3.connect('weather_forecast.db', check_same_thread=False)
c = conn.cursor()

# テーブルの作成
def initialize_db():
    c.execute('''
    CREATE TABLE IF NOT EXISTS regions (
        id INTEGER PRIMARY KEY,
        name TEXT UNIQUE
    )''')
    c.execute('''
    CREATE TABLE IF NOT EXISTS offices (
        id INTEGER PRIMARY KEY,
        region_id INTEGER,
        name TEXT,
        FOREIGN KEY(region_id) REFERENCES regions(id)
    )''')
    c.execute('''
    CREATE TABLE IF NOT EXISTS forecasts (
        id INTEGER PRIMARY KEY,
        office_id INTEGER,
        publishing_office TEXT,
        report_datetime TEXT,
        area_name TEXT,
        weather TEXT,
        created_at TEXT,
        FOREIGN KEY(office_id) REFERENCES offices(id)
    )''')
    conn.commit()

initialize_db()

def main(page: ft.Page):
    page.scroll = ft.ScrollMode.AUTO

    with open('jma/areas.json', 'r', encoding='utf-8') as f:
        area_data = json.load(f)

    # データベースへの地域情報の保存
    regions = {}
    for key, value in area_data["centers"].items():
        region_name = value['name']
        c.execute('INSERT OR IGNORE INTO regions (name) VALUES (?)', (region_name,))
        regions_db_index = c.lastrowid
        regions[region_name] = {}

    for key, value in area_data["offices"].items():
        parent_center = value['parent']
        if parent_center in area_data['centers']:
            region_name = area_data['centers'][parent_center]['name']
            office_name = value['name']
            c.execute('INSERT OR IGNORE INTO offices (region_id, name) VALUES ((SELECT id FROM regions WHERE name = ?), ?)', (region_name, office_name))
            regions[region_name][key] = office_name

    conn.commit()

    selected_region = None

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

    def update_office_dropdown(region):
        nonlocal selected_region
        selected_region = region
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
                save_forecast_data(area_code, forecast_data)
                display_forecast(forecast_data)
            else:
                output.value = f"Error: {response.status_code}"
                page.update()

    def save_forecast_data(area_code, data):
        office_name = regions[selected_region][area_code]
        c.execute('SELECT id FROM offices WHERE name = ?', (office_name,))
        office_id = c.fetchone()[0]
        for entry in data:
            publishing_office = entry.get("publishingOffice", "不明")
            report_datetime = entry.get("reportDatetime", "不明")
            for time_series in entry.get("timeSeries", []):
                for area in time_series.get("areas", []):
                    area_name = area.get("area", {}).get("name", "不明")
                    weather = area.get("weathers", ["情報なし"])[0]
                    created_at = datetime.now().isoformat()
                    c.execute('''
                    INSERT INTO forecasts (office_id, publishing_office, report_datetime, area_name, weather, created_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                    ''', (office_id, publishing_office, report_datetime, area_name, weather, created_at))
        conn.commit()

    def display_forecast(data):
        page.controls.clear()
        page.controls.append(ft.Row([back_button]))
        for entry in data:
            publishing_office = entry.get("publishingOffice", "不明")
            report_datetime = entry.get("reportDatetime", "不明")
            title = ft.Text(f"{publishing_office} {report_datetime}", style=ft.TextStyle(size=24, weight="bold"))
            page.controls.append(title)
            for time_series in entry.get("timeSeries", []):
                for area in time_series.get("areas", []):
                    area_name = area.get("area", {}).get("name", "不明")
                    weather = area.get("weathers", ["情報なし"])[0]
                    weather_text = ft.Text(f"地域: {area_name} 天気: {weather}")
                    page.controls.append(weather_text)
        page.update()

    def show_area_selection(e=None):
        page.controls.clear()
        page.controls.append(ft.Column([region_dropdown, office_dropdown, output]))
        page.update()

    back_button = ft.ElevatedButton(text="戻る", on_click=show_area_selection)

    show_area_selection()

ft.app(target=main)