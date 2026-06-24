import reflex as rx

config = rx.Config(
    app_name="Administracion_Finca",
    api_url="http://192.168.0.104:8000",
    plugins=[
        rx.plugins.SitemapPlugin(),
        rx.plugins.TailwindV4Plugin(),
    ]
)