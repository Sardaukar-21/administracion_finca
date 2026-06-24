# Administracion_Finca/views/ia.py
import reflex as rx
import backend_animales
import backend_ia
from . import styles

class IAState(rx.State):
    """Gestor de Estado modular para la Inteligencia Artificial y predicciones."""
    
    # --- Datos de la Tabla ---
    datos_biometricos_ia: list[list] = []
    busqueda: str = ""
    
    # --- Auditoría Clínico-Zootécnica Individual ---
    cargando_auditoria: bool = False
    dialogo_auditoria_abierto: bool = False
    codigo_auditado: str = ""
    resultado_salud: str = ""
    resultado_diagnostico: str = ""
    resultado_requerimiento: str = ""
    
    # --- Reporte Gerencial de la Finca ---
    cargando_gerencial: bool = False
    reporte_generado: bool = False
    reporte_advertencia: str = ""
    reporte_estrategia: str = ""

    @rx.var
    def datos_grafica_peso(self) -> list[dict]:
        datos = []
        for fila in self.datos_biometricos_ia:
            try:
                codigo = str(fila[1])
                peso_actual = float(fila[2])
                consumo = float(fila[3])
                peso_proyectado = round(peso_actual + (consumo * 1.8), 2)
                datos.append({
                    "name": codigo,
                    "Actual": round(peso_actual, 2),
                    "Proyectado": peso_proyectado
                })
            except (IndexError, ValueError, TypeError):
                continue
        return datos

    def cambiar_busqueda(self, valor: str):
        self.busqueda = valor

    @rx.var
    def datos_biometricos_ia_filtrados(self) -> list[list]:
        if self.busqueda.strip() == "":
            return self.datos_biometricos_ia
        termino = self.busqueda.strip().lower()
        return [
            row for row in self.datos_biometricos_ia
            if (termino in str(row[0]).lower()) or (termino in str(row[1]).lower())
        ]

    async def cargar_datos(self):
        """Consulta los datos biométricos para alimentar la tabla de IA."""
        def operacion_db():
            return backend_animales.obtener_datos_biometricos_ia()
        raw_ia = await rx.run_in_thread(operacion_db)
        self.datos_biometricos_ia = raw_ia

    async def auditar_animal(self, id_animal: int, codigo: str):
        """Dispara el análisis individual del animal conectando con el proveedor de IA."""
        self.codigo_auditado = codigo
        self.dialogo_auditoria_abierto = True
        self.cargando_auditoria = True
        self.resultado_salud = ""
        self.resultado_diagnostico = ""
        self.resultado_requerimiento = ""
        yield
        
        def operacion_ia():
            return backend_ia.generar_diagnostico_ia(id_animal)
            
        exito, resultado = await rx.run_in_thread(operacion_ia)
        
        self.resultado_salud = resultado.get("estado_salud", "alerta").lower()
        self.resultado_diagnostico = resultado.get("diagnostico", "No se pudo compilar el diagnóstico.")
        self.resultado_requerimiento = resultado.get("requerimiento", "Revise la configuración del proveedor de IA en el archivo .env.")
        self.cargando_auditoria = False

    def cerrar_auditoria(self):
        self.dialogo_auditoria_abierto = False

    async def generar_reporte_gerencial(self):
        """Genera el reporte macro de riesgos y producción de la finca."""
        self.reporte_generado = False
        self.cargando_gerencial = True
        self.reporte_advertencia = ""
        self.reporte_estrategia = ""
        yield
        
        from Administracion_Finca.views.alimentacion import AlimentacionState
        alim_state = await self.get_state(AlimentacionState)
        try:
            costo_val = float(alim_state.costo_por_kg) if alim_state.costo_por_kg else 0.50
        except ValueError:
            costo_val = 0.50
            
        def operacion_gerencial():
            return backend_ia.generar_reporte_gerencial_ia(costo_val)
            
        exito, resultado = await rx.run_in_thread(operacion_gerencial)
        
        self.reporte_advertencia = resultado.get("advertencia_riesgo", "No se pudo generar la advertencia.")
        self.reporte_estrategia = resultado.get("estrategia_produccion", "No se pudo generar la estrategia.")
        self.reporte_generado = True
        self.cargando_gerencial = False

    async def descargar_reporte_pdf(self):
        """Genera y descarga el reporte gerencial completo en formato PDF."""
        from Administracion_Finca.views.alimentacion import AlimentacionState
        alim_state = await self.get_state(AlimentacionState)
        try:
            costo_val = float(alim_state.costo_por_kg) if alim_state.costo_por_kg else 0.50
        except ValueError:
            costo_val = 0.50
            
        import backend_reporte_pdf
        def generar():
            return backend_reporte_pdf.generar_pdf_gerencial(costo_val)
            
        pdf_bytes = await rx.run_in_thread(generar)
        return rx.download(
            filename="Reporte_Gerencial_Finca.pdf",
            data=pdf_bytes
        )


# --- Tokens de color semánticos centralizados ---
_card_bg     = styles.card_bg
_card_border = styles.card_border
_text_main   = styles.text_main
_text_muted  = styles.text_muted
_text_sub    = styles.text_sub

# Tarjeta de riesgo (roja)
_risk_bg     = styles.risk_bg
_risk_border = styles.risk_border
_risk_title  = styles.risk_title
_risk_text   = styles.risk_text

# Tarjeta de estrategia (verde)
_strategy_bg     = styles.strategy_bg
_strategy_border = styles.strategy_border
_strategy_title  = styles.strategy_title
_strategy_text   = styles.strategy_text

# Modal de diagnóstico
_diag_box_bg     = styles.diag_box_bg
_diag_box_border = styles.diag_box_border
_req_box_bg      = styles.req_box_bg
_req_box_border  = styles.req_box_border
_req_text        = styles.req_text


# --- Componentes Visuales ---

def elemento_tabla_ia(registro: rx.Var[list]) -> rx.Component:
    """Fila para cada animal en la tabla de predicciones e IA."""
    id_animal = registro[0].to(int)
    codigo = registro[1].to(str)
    peso_actual = registro[2].to(float)
    consumo = registro[3].to(float)
    fecha_pesaje = registro[4]

    peso_proyectado_30d = (peso_actual + (consumo * 1.8)).to_string()

    return rx.table.row(
        rx.table.cell(codigo, font_weight="bold", color=_text_main),
        rx.table.cell(peso_actual.to_string() + " kg", color=rx.color_mode_cond(light="#1d4ed8", dark="#60a5fa")),
        rx.table.cell(consumo.to_string() + " kg/día", color=_text_sub),
        rx.table.cell(fecha_pesaje, color=_text_muted),
        rx.table.cell(
            rx.badge(peso_proyectado_30d + " kg", color_scheme="purple", variant="solid")
        ),
        rx.table.cell(
            rx.tooltip(
                rx.button(
                    rx.hstack(
                        rx.icon("brain", size=14),
                        rx.text("Auditar con IA"),
                        spacing="1",
                        align="center"
                    ),
                    on_click=lambda: IAState.auditar_animal(id_animal, codigo),
                    color_scheme="purple",
                    size="1",
                    variant="solid",
                    cursor="pointer"
                ),
                content="Generar informe clínico y recomendaciones por IA para este ejemplar",
            )
        )
    )


def ia_view() -> rx.Component:
    """Vista principal para la pestaña de Predicciones y Consultas IA."""
    return rx.vstack(
        # --- BLOQUE 1: Reporte Gerencial de la Finca (Macro) ---
        rx.card(
            rx.vstack(
                rx.hstack(
                    rx.icon("chart-bar", color="#a855f7", size=22),
                    rx.heading("Auditoría de Riesgos Colectivos y Estrategia de la Finca", size="3", color=_text_main),
                    spacing="2",
                    align="center"
                ),
                rx.text(
                    "Analiza los costos acumulados y detecta la omisión de vacunas de cumplimiento nacional obligatorio (Fiebre Aftosa) usando modelos de IA.",
                    font_size="0.85em",
                    color=_text_muted
                ),

                rx.cond(
                    ~IAState.reporte_generado,
                    # Estado Inicial
                    rx.center(
                        rx.flex(
                            rx.button(
                                rx.hstack(
                                    rx.icon("sparkles", size=18),
                                    rx.text("Generar Reporte Gerencial con IA"),
                                    spacing="2"
                                ),
                                on_click=IAState.generar_reporte_gerencial,
                                loading=IAState.cargando_gerencial,
                                color_scheme="purple",
                                size="3",
                                cursor="pointer",
                                width={"initial": "100%", "sm": "auto"},
                            ),
                            rx.button(
                                rx.hstack(
                                    rx.icon("file-down", size=18),
                                    rx.text("Descargar Reporte PDF"),
                                    spacing="2"
                                ),
                                on_click=IAState.descargar_reporte_pdf,
                                color_scheme="red",
                                size="3",
                                cursor="pointer",
                                width={"initial": "100%", "sm": "auto"},
                            ),
                            spacing="4",
                            margin_y="20px",
                            direction={"initial": "column", "sm": "row"},
                            width="100%",
                            justify="center",
                            align="center"
                        ),
                        width="100%"
                    ),
                    # Reporte Generado
                    rx.vstack(
                        rx.grid(
                            # Tarjeta de Riesgos Sanitarios
                            rx.card(
                                rx.vstack(
                                    rx.hstack(
                                        rx.icon("triangle-alert", color=_risk_title, size=18),
                                        rx.text("Advertencia de Riesgos Sanitarios", weight="bold", font_size="0.9em", color=_risk_title),
                                        spacing="1"
                                    ),
                                    rx.markdown(IAState.reporte_advertencia, font_size="0.85em", color=_risk_text),
                                    spacing="2",
                                    align_items="start"
                                ),
                                background_color=_risk_bg,
                                border=_risk_border,
                                padding="16px"
                            ),
                            # Tarjeta de Estrategia
                            rx.card(
                                rx.vstack(
                                    rx.hstack(
                                        rx.icon("trending-up", color=_strategy_title, size=18),
                                        rx.text("Estrategia Zootécnica y de Producción", weight="bold", font_size="0.9em", color=_strategy_title),
                                        spacing="1"
                                    ),
                                    rx.markdown(IAState.reporte_estrategia, font_size="0.85em", color=_strategy_text),
                                    spacing="2",
                                    align_items="start"
                                ),
                                background_color=_strategy_bg,
                                border=_strategy_border,
                                padding="16px"
                            ),
                            columns={"initial": "1", "md": "2"},
                            spacing="4",
                            width="100%",
                            margin_top="15px",
                            align="start",
                        ),
                        rx.flex(
                            rx.button(
                                rx.hstack(
                                    rx.icon("file-down", size=16),
                                    rx.text("Descargar Reporte PDF"),
                                    spacing="1",
                                    align="center"
                                ),
                                on_click=IAState.descargar_reporte_pdf,
                                color_scheme="red",
                                size="1",
                                cursor="pointer",
                                width={"initial": "100%", "sm": "auto"},
                            ),
                            rx.button(
                                "Volver a Analizar Finca",
                                on_click=IAState.generar_reporte_gerencial,
                                loading=IAState.cargando_gerencial,
                                variant="soft",
                                color_scheme="purple",
                                size="1",
                                cursor="pointer",
                                width={"initial": "100%", "sm": "auto"},
                            ),
                            direction={"initial": "column", "sm": "row"},
                            spacing="3",
                            width="100%",
                            justify="between",
                            align="center"
                        ),
                        spacing="2",
                        width="100%"
                    )
                ),
                width="100%",
                spacing="3"
            ),
            border_top="4px solid #a855f7",
            background_color=_card_bg,
            border_left=_card_border,
            border_right=_card_border,
            border_bottom=_card_border,
            border_radius="0 0 12px 12px",
            padding="20px",
            width="100%",
            margin_bottom="15px"
        ),

        # --- BLOQUE 2: Tabla de Proyecciones e IA Individual ---
        rx.card(
            rx.vstack(
                rx.hstack(
                    rx.heading("Predicciones de Peso e Informes Clínicos Individuales", size="3", color=_text_main),
                    rx.spacer(),
                    rx.input(
                        placeholder="Buscar...",
                        value=IAState.busqueda,
                        on_change=IAState.cambiar_busqueda,
                        size="1",
                        width="160px",
                        background_color=styles.input_bg,
                    ),
                    width="100%",
                    align_items="center",
                ),
                rx.text(
                    "Monitorea el desarrollo zootécnico y ejecuta auditorías clínicas por Inteligencia Artificial para cada animal activo.",
                    font_size="0.85em",
                    color=_text_muted,
                    margin_bottom="10px"
                ),

                rx.box(
                    rx.table.root(
                        rx.table.header(
                            rx.table.row(
                                rx.table.column_header_cell("Código Animal", color=_text_muted),
                                rx.table.column_header_cell("Último Peso", color=_text_muted),
                                rx.table.column_header_cell("Consumo Alimento", color=_text_muted),
                                rx.table.column_header_cell("Fecha Pesaje", color=_text_muted),
                                rx.table.column_header_cell("Proyección Peso (30 días)", color="#a855f7"),
                                rx.table.column_header_cell("Auditoría Veterinaria", color=_text_muted),
                            )
                        ),
                        rx.table.body(
                            rx.foreach(
                                IAState.datos_biometricos_ia_filtrados,
                                elemento_tabla_ia
                            )
                        ),
                        width="100%",
                        variant="surface"
                    ),
                    overflow_x="auto",
                    width="100%",
                ),
                width="100%"
            ),
            background_color=_card_bg,
            border=_card_border,
            padding="20px",
            width="100%"
        ),

        # --- BLOQUE 3: Gráfica de Proyección Biométrica (Desarrollo Zootécnico) ---
        rx.card(
            rx.vstack(
                rx.hstack(
                    rx.icon("trending-up", color="#a855f7", size=22),
                    rx.heading("Proyección de Desarrollo de Peso (Ganancia de Peso a 30 días)", size="3", color=_text_main),
                    spacing="2",
                    align="center"
                ),
                rx.text(
                    "Comparativa entre el peso actual registrado de cada animal y el peso proyectado según su tasa de consumo alimenticio actual.",
                    font_size="0.85em",
                    color=_text_muted,
                    margin_bottom="15px"
                ),
                rx.cond(
                    IAState.datos_biometricos_ia.length() == 0,
                    rx.center(
                        rx.text("No hay suficientes datos biométricos de animales activos para mostrar la proyección.", color=_text_muted, font_size="0.85em"),
                        width="100%",
                        padding_y="20px"
                    ),
                    rx.recharts.responsive_container(
                        rx.recharts.bar_chart(
                            rx.recharts.bar(
                                data_key="Actual",
                                fill=rx.color_mode_cond(light="#3b82f6", dark="#60a5fa"),
                                radius=[4, 4, 0, 0],
                            ),
                            rx.recharts.bar(
                                data_key="Proyectado",
                                fill=rx.color_mode_cond(light="#a855f7", dark="#c084fc"),
                                radius=[4, 4, 0, 0],
                            ),
                            rx.recharts.x_axis(data_key="name", stroke=rx.color_mode_cond(light="#64748b", dark="#9ca3af"), font_size=10),
                            rx.recharts.y_axis(stroke=rx.color_mode_cond(light="#64748b", dark="#9ca3af"), font_size=10),
                            rx.recharts.cartesian_grid(stroke_dasharray="3 3", stroke=rx.color_mode_cond(light="#e2e8f0", dark="#374151")),
                            rx.recharts.legend(vertical_align="top", height=36, font_size=11),
                            rx.recharts.graphing_tooltip(),
                            data=IAState.datos_grafica_peso,
                        ),
                        width="99%",
                        height=300,
                    )
                ),
                width="100%"
            ),
            background_color=_card_bg,
            border=_card_border,
            padding="20px",
            width="100%",
            margin_top="15px"
        ),

        # --- Modal para Auditoría Clínica Individual ---
        rx.dialog.root(
            rx.dialog.content(
                rx.cond(
                    IAState.cargando_auditoria,
                    # Cargando
                    rx.center(
                        rx.vstack(
                            rx.spinner(size="3", color="#a855f7"),
                            rx.text("Consultando historial clínico, biometría y reglas INSAI...", color=_text_sub, font_size="0.9em"),
                            rx.text("Esto puede tardar unos segundos dependiendo del proveedor de IA.", color=_text_muted, font_size="0.75em"),
                            spacing="3",
                            align="center",
                            padding_y="30px"
                        ),
                        width="100%"
                    ),
                    # Auditoría Cargada
                    rx.vstack(
                        rx.dialog.title("Informe Clínico IA - Animal ", IAState.codigo_auditado, color=_text_main),

                        rx.hstack(
                            rx.text("Estado de Salud:", weight="bold", font_size="0.85em", color=_text_muted),
                            rx.cond(IAState.resultado_salud == "optimo", rx.badge("Óptimo", color_scheme="green", variant="solid")),
                            rx.cond(IAState.resultado_salud == "alerta", rx.badge("Alerta Sanitaria", color_scheme="yellow", variant="solid")),
                            rx.cond(IAState.resultado_salud == "critico", rx.badge("Crítico", color_scheme="red", variant="solid")),
                            spacing="2",
                            align="center"
                        ),

                        # Cuadro de Diagnóstico
                        rx.text("Diagnóstico Detallado:", weight="bold", font_size="0.85em", color=_text_sub, margin_top="10px"),
                        rx.card(
                            rx.text(IAState.resultado_diagnostico, font_size="0.85em", color=_text_sub),
                            background_color=_diag_box_bg,
                            border=_diag_box_border,
                            padding="12px",
                            width="100%"
                        ),

                        # Cuadro de Requerimiento/Acción
                        rx.text("Acción Inmediata Recomendada:", weight="bold", font_size="0.85em", color=_text_sub, margin_top="10px"),
                        rx.card(
                            rx.hstack(
                                rx.icon("zap", color="#a855f7", size=16),
                                rx.text(IAState.resultado_requerimiento, font_size="0.85em", color=_req_text, weight="bold"),
                                spacing="2",
                                align="center"
                            ),
                            background_color=_req_box_bg,
                            border=_req_box_border,
                            padding="12px",
                            width="100%"
                        ),

                        # Botón Cerrar
                        rx.hstack(
                            rx.spacer(),
                            rx.button("Entendido / Cerrar", color_scheme="purple", on_click=IAState.cerrar_auditoria, cursor="pointer"),
                            width="100%",
                            margin_top="15px"
                        ),
                        spacing="3",
                        align_items="start",
                        width="100%"
                    )
                ),
                max_width="550px",
                padding="20px"
            ),
            open=IAState.dialogo_auditoria_abierto
        ),
        spacing="4",
        width="100%"
    )
