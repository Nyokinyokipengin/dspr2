import flet as ft
import requests
import json

def main(page: ft.Page):
    page.scroll = ft.ScrollMode.AUTO

    # 地域データのロード
    with open('jma/areas.json', 'r', encoding='utf-8') as f:
        area_data = json.load(f)

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
                display_forecast(forecast_data)
            else:
                output.value = f"Error: {response.status_code}"
                page.update()

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

    # 「戻る」ボタン
    back_button = ft.ElevatedButton(text="戻る", on_click=show_area_selection)

    # 地域選択画面を初期表示
    show_area_selection()

ft.app(target=main)
