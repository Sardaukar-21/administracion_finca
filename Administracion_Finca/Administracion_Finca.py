import reflex as rx
import sys
import os

# Forzar la ruta absoluta del directorio raíz del proyecto
ruta_actual = os.path.dirname(os.path.abspath(__file__))
ruta_raiz = os.path.abspath(os.path.join(ruta_actual, '..'))

if ruta_raiz not in sys.path:
    sys.path.insert(0, ruta_raiz)

from Administracion_Finca.views.animales import animales_view, AnimalesState
from Administracion_Finca.views.vacunacion import vacunacion_view, VacunacionState
from Administracion_Finca.views.alimentacion import alimentacion_view, AlimentacionState
from Administracion_Finca.views.ia import ia_view, IAState


class AppState(rx.State):
    """Estado global de la aplicación para el header."""
    hora_actual: str = ""

    @rx.event(background=True)
    async def actualizar_reloj(self):
        import asyncio
        from datetime import datetime
        while True:
            async with self:
                self.hora_actual = datetime.now().strftime("%d/%m/%Y  %H:%M:%S")
            await asyncio.sleep(1)


def header() -> rx.Component:
    """Header premium de la aplicación con logo, título y reloj en vivo."""
    return rx.box(
        rx.hstack(
            # Logo + título
            rx.hstack(
                rx.box(
                    rx.icon("tractor", color="#34d399", size=22),
                    background="linear-gradient(135deg, #064e3b 0%, #065f46 100%)",
                    padding="8px",
                    border_radius="10px",
                    box_shadow="0 2px 8px rgba(52,211,153,0.30)",
                    display="flex",
                    align_items="center",
                    justify_content="center",
                ),
                rx.vstack(
                    rx.hstack(
                        rx.text(
                            "Admi",
                            font_size="1.25em",
                            font_weight="500",
                            color=rx.color_mode_cond(light="#0f172a", dark="#f9fafb"),
                            letter_spacing="-0.3px",
                            line_height="1",
                        ),
                        rx.text(
                            "Finca",
                            font_size="1.25em",
                            font_weight="800",
                            color="#34d399",
                            letter_spacing="-0.3px",
                            line_height="1",
                        ),
                        spacing="0",
                        align="baseline",
                    ),
                    rx.text(
                        "Panel de Gestión Gerencial",
                        font_size="0.72em",
                        color=rx.color_mode_cond(light="#64748b", dark="#9ca3af"),
                        line_height="1",
                    ),
                    spacing="1",
                    align_items="start",
                ),
                spacing="3",
                align="center",
            ),
            rx.spacer(),
            # Reloj en vivo
            rx.hstack(
                rx.icon("clock", size=14, color=rx.color_mode_cond(light="#64748b", dark="#6b7280")),
                rx.text(
                    AppState.hora_actual,
                    font_size="0.78em",
                    font_family="'JetBrains Mono', 'Courier New', monospace",
                    color=rx.color_mode_cond(light="#475569", dark="#9ca3af"),
                    letter_spacing="0.5px",
                ),
                spacing="1",
                align="center",
                display=["none", "none", "flex"],
            ),
            # Separador vertical
            rx.box(
                width="1px",
                height="24px",
                background_color=rx.color_mode_cond(light="#e2e8f0", dark="#374151"),
                margin_x="8px",
                display=["none", "none", "block"],
            ),
            rx.color_mode.button(size="2"),
            padding="14px 20px",
            background_color=rx.color_mode_cond(light="#ffffff", dark="#1f2937"),
            box_shadow=rx.color_mode_cond(
                light="0 1px 0 0 #e2e8f0, 0 2px 8px rgba(0,0,0,0.04)",
                dark="0 1px 0 0 #374151",
            ),
            width="100%",
            align="center",
        ),
        width="100%",
        position="sticky",
        top="0",
        z_index="100",
    )


@rx.page(
    route="/",
    on_load=[
        AppState.actualizar_reloj,
        IAState.cargar_datos,
        AnimalesState.cargar_datos,
        VacunacionState.cargar_datos,
        AlimentacionState.cargar_datos,
    ],
    title="AdmiFinca | Panel Gerencial",
    description="Sistema de gestión integral para la administración de fincas ganaderas.",
)
def index() -> rx.Component:
    return rx.box(
        # Fuentes de Google (Inter + JetBrains Mono para el reloj)
        rx.html(
            "<link rel='preconnect' href='https://fonts.googleapis.com'>"
            "<link rel='preconnect' href='https://fonts.gstatic.com' crossorigin>"
            "<link href='https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap' rel='stylesheet'>"
        ),
        header(),
        rx.center(
            rx.vstack(
                rx.tabs.root(
                    rx.tabs.list(
                        rx.tabs.trigger(
                            rx.hstack(
                                rx.icon("list", size=15),
                                rx.text("Animales"),
                                rx.badge(
                                    AnimalesState.total_animales,
                                    color_scheme="green",
                                    variant="solid",
                                    radius="full",
                                    size="1",
                                ),
                                spacing="1",
                                align="center",
                            ),
                            value="tab_animales",
                            flex_shrink="0",
                        ),
                        rx.tabs.trigger(
                            rx.hstack(
                                rx.icon("shield-check", size=15),
                                rx.text("Vacunación"),
                                rx.cond(
                                    AnimalesState.alertas_sanitarias_count > 0,
                                    rx.badge(
                                        AnimalesState.alertas_sanitarias_count,
                                        color_scheme="red",
                                        variant="solid",
                                        radius="full",
                                        size="1",
                                    ),
                                ),
                                spacing="1",
                                align="center",
                            ),
                            value="tab_vacunas",
                            flex_shrink="0",
                        ),
                        rx.tabs.trigger(
                            rx.hstack(
                                rx.icon("trending-up", size=15),
                                rx.text("Alimentación"),
                                spacing="1",
                                align="center",
                            ),
                            value="tab_alimentacion",
                            flex_shrink="0",
                        ),
                        rx.tabs.trigger(
                            rx.hstack(
                                rx.icon("sparkles", size=15),
                                rx.text("IA"),
                                spacing="1",
                                align="center",
                            ),
                            value="tab_ia",
                            flex_shrink="0",
                        ),
                        width="100%",
                        overflow_x="auto",
                    ),
                    rx.tabs.content(
                        rx.box(animales_view(), padding_y="15px"),
                        value="tab_animales",
                    ),
                    rx.tabs.content(
                        rx.box(vacunacion_view(), padding_y="15px"),
                        value="tab_vacunas",
                    ),
                    rx.tabs.content(
                        rx.box(alimentacion_view(), padding_y="15px"),
                        value="tab_alimentacion",
                    ),
                    rx.tabs.content(
                        rx.box(ia_view(), padding_y="15px"),
                        value="tab_ia",
                    ),
                    width="100%",
                    default_value="tab_animales",
                ),
                spacing="4",
                width="100%",
                max_width="1200px",
                padding_x=["16px", "24px", "32px"],
                padding_y="3%",
            ),
        ),
        rx.toast.provider(),
        width="100%",
        overflow_x="hidden",
        min_height="100vh",
        background_color=rx.color_mode_cond(light="#f1f5f9", dark="#111827"),
        font_family="'Inter', system-ui, -apple-system, sans-serif",
    )

app = rx.App()
app.add_page(index)