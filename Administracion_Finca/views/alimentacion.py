# Administracion_Finca/views/alimentacion.py
import reflex as rx
import re
import backend_alimentacion
from . import styles

class AlimentacionState(rx.State):
    """Gestor de Estado modular para la alimentación y finanzas de la finca."""
    
    # --- Configuración Financiera ---
    costo_por_kg: str = "0.50"
    
    # --- KPIs Proyectados ---
    total_kg: float = 0.0
    costo_diario_usd: float = 0.0
    costo_mensual_usd: float = 0.0
    
    @rx.var
    def total_kg_fmt(self) -> str:
        return f"{self.total_kg:,.2f}"

    @rx.var
    def costo_diario_fmt(self) -> str:
        return f"{self.costo_diario_usd:,.2f}"

    @rx.var
    def costo_mensual_fmt(self) -> str:
        return f"{self.costo_mensual_usd:,.2f}"

    @rx.var
    def datos_grafica_consumo(self) -> list[dict]:
        datos = []
        colores_barras = [
            "#10b981",  # Emerald/Green
            "#3b82f6",  # Blue
            "#f59e0b",  # Amber/Orange
            "#8b5cf6",  # Violet/Purple
            "#ec4899",  # Pink
            "#14b8a6",  # Teal
            "#f43f5e",  # Rose
            "#06b6d4"   # Cyan
        ]
        for i, fila in enumerate(self.lista_detalle_alimentacion):
            try:
                nombre = str(fila[1])
                consumo = float(fila[4])
                color = colores_barras[i % len(colores_barras)]
                datos.append({"name": nombre, "consumo": consumo, "fill": color})
            except (IndexError, ValueError, TypeError):
                continue
        return datos

    @rx.var
    def datos_grafica_dietas(self) -> list[dict]:
        dietas_count = {}
        for fila in self.lista_detalle_alimentacion:
            try:
                dieta = str(fila[5])
                if not dieta or dieta.strip() == "":
                    dieta = "Sin Dieta"
                dietas_count[dieta] = dietas_count.get(dieta, 0) + 1
            except (IndexError, ValueError, TypeError):
                continue

        # Paleta de colores predefinida para dietas comunes
        colores_predeterminados = {
            "alimento": "#f59e0b",          # Amber/Naranja para alimento balanceado
            "perrarina": "#3b82f6",         # Azul para Perrarina
            "pasto": "#10b981",             # Verde para Pasto
            "forraje": "#10b981",           # Verde para Forraje
            "pasto natural / forraje": "#10b981", # Verde para Pasto/Forraje
            "sin dieta": "#9ca3af",         # Gris para sin dieta
        }

        # Paleta secuencial para otras dietas no mapeadas
        paleta_adicional = [
            "#6366f1",  # Indigo
            "#8b5cf6",  # Violeta
            "#ec4899",  # Rosa
            "#14b8a6",  # Teal
            "#f43f5e",  # Rose
            "#06b6d4"   # Cyan
        ]

        resultado = []
        for i, (nombre, valor) in enumerate(dietas_count.items()):
            nombre_lower = nombre.lower().strip()
            color = None
            for clave, val_color in colores_predeterminados.items():
                if clave in nombre_lower:
                    color = val_color
                    break
            
            if color is None:
                color = paleta_adicional[i % len(paleta_adicional)]
                
            resultado.append({"name": nombre, "value": valor, "fill": color})
        return resultado
    
    # --- Datos de los Animales ---
    lista_detalle_alimentacion: list[list] = []
    busqueda: str = ""
    
    # --- Alertas ---
    guardando: bool = False
    
    # --- Modal de Edición ---
    dialogo_abierto: bool = False
    id_animal_seleccionado: int = 0
    codigo_animal_seleccionado: str = ""
    nuevo_tipo_alimento: str = ""

    async def cargar_datos(self):
        """Pobla los datos financieros y de alimentación desde el backend."""
        try:
            costo_val = float(self.costo_por_kg) if self.costo_por_kg else 0.0
        except ValueError:
            costo_val = 0.50
            
        def operacion_totales():
            return backend_alimentacion.calcular_totales_alimentacion_finca(costo_val)
            
        def operacion_detalles():
            return backend_alimentacion.obtener_detalle_alimentacion_animales()
            
        totales = await rx.run_in_thread(operacion_totales)
        self.total_kg = totales.get("total_kg", 0.0)
        self.costo_diario_usd = totales.get("costo_diario_usd", 0.0)
        self.costo_mensual_usd = totales.get("costo_mensual_usd", 0.0)
        
        import datetime
        detalles = await rx.run_in_thread(operacion_detalles)
        detalles_formateados = []
        for fila in detalles:
            try:
                peso = round(float(fila[3]), 2)
                consumo = round(float(fila[4]), 2)
                id_especie = int(fila[6])
                nacimiento_str = fila[7]
                
                # Calcular edad en meses
                if nacimiento_str:
                    nacimiento = datetime.datetime.strptime(nacimiento_str, "%Y-%m-%d").date()
                    edad_meses = (datetime.date.today() - nacimiento).days // 30
                else:
                    edad_meses = 12
            except (ValueError, TypeError, IndexError):
                peso = 0.0
                consumo = 0.0
                id_especie = 1
                edad_meses = 12
                
            # Determinar rangos de peso ideal
            peso_min, peso_max = 0.0, 0.0
            con_pct_min, con_pct_max = 0.02, 0.03  # Porcentaje de consumo por defecto
            
            if id_especie == 1:  # Bovino
                con_pct_min, con_pct_max = 0.02, 0.03
                if edad_meses < 12:
                    peso_min, peso_max = 70.0, 300.0
                elif edad_meses <= 24:
                    peso_min, peso_max = 180.0, 450.0
                else:
                    peso_min, peso_max = 350.0, 1000.0
            elif id_especie == 2:  # Porcino
                con_pct_min, con_pct_max = 0.03, 0.05
                if edad_meses < 3:
                    peso_min, peso_max = 10.0, 35.0
                elif edad_meses <= 8:
                    peso_min, peso_max = 45.0, 130.0
                else:
                    peso_min, peso_max = 90.0, 350.0
            elif id_especie == 3:  # Ovino
                con_pct_min, con_pct_max = 0.02, 0.04
                if edad_meses < 6:
                    peso_min, peso_max = 12.0, 40.0
                else:
                    peso_min, peso_max = 30.0, 75.0
                    
            # Calcular consumo ideal en kg/día
            con_min = round(peso * con_pct_min, 2)
            con_max = round(peso * con_pct_max, 2)
            
            # Formatear rangos como texto legible
            rango_peso = f"{int(peso_min)}-{int(peso_max)} kg"
            rango_consumo = f"{con_min:.2f}-{con_max:.2f} kg"
            
            # Validaciones rápidas de salud
            estado_peso = "bueno"  # bueno, bajo, alto
            if peso < peso_min:
                estado_peso = "bajo"
            elif peso > peso_max:
                estado_peso = "alto"
                
            estado_consumo = "bueno"  # bueno, bajo, alto
            if con_min > 0:
                if consumo < con_min:
                    estado_consumo = "bajo"
                elif consumo > con_max:
                    estado_consumo = "alto"
            
            detalles_formateados.append([
                fila[0],             # id_animal
                fila[1],             # numero_identificacion
                fila[2],             # especie
                peso,                # peso actual
                consumo,             # consumo actual
                fila[5],             # dieta
                rango_peso,          # rango peso ideal
                rango_consumo,       # rango consumo ideal
                estado_peso,         # estado del peso
                estado_consumo,      # estado del consumo
            ])
        self.lista_detalle_alimentacion = detalles_formateados

    async def cambiar_costo(self, valor: str):
        if valor == "":
            self.costo_por_kg = ""
            return
        patron = r"^\d*\.?\d{0,2}$"
        if re.match(patron, valor):
            self.costo_por_kg = valor
            if not valor.endswith('.'):
                await self.cargar_datos()

    def cambiar_busqueda(self, valor: str):
        self.busqueda = valor

    @rx.var
    def lista_detalle_alimentacion_filtrada(self) -> list[list]:
        if self.busqueda.strip() == "":
            return self.lista_detalle_alimentacion
        termino = self.busqueda.strip().lower()
        return [
            row for row in self.lista_detalle_alimentacion
            if (termino in str(row[0]).lower()) or (termino in str(row[1]).lower())
        ]

    def abrir_editor_dieta(self, id_animal: int, codigo: str, dieta_actual: str):
        self.id_animal_seleccionado = id_animal
        self.codigo_animal_seleccionado = codigo
        self.nuevo_tipo_alimento = dieta_actual
        self.dialogo_abierto = True

    def cerrar_editor_dieta(self):
        self.dialogo_abierto = False

    def cambiar_nuevo_tipo_alimento(self, valor: str):
        self.nuevo_tipo_alimento = valor

    async def guardar_dieta(self):
        dieta_limpia = self.nuevo_tipo_alimento.strip()
        if not dieta_limpia:
            yield rx.toast.error("El tipo de alimento o dieta no puede estar vacío.")
            return
        if len(dieta_limpia) < 2:
            yield rx.toast.warning("La descripción de la dieta debe tener al menos 2 caracteres.")
            return
        if len(dieta_limpia) > 120:
            yield rx.toast.warning("La descripción de la dieta no puede superar los 120 caracteres.")
            return
            
        self.guardando = True
        yield

        def operacion_bd():
            return backend_alimentacion.registrar_tipo_alimento(
                self.id_animal_seleccionado, 
                self.nuevo_tipo_alimento.strip()
            )
            
        exito = await rx.run_in_thread(operacion_bd)
        
        self.guardando = False
        if exito:
            yield rx.toast.success(f"¡Dieta del animal {self.codigo_animal_seleccionado} actualizada exitosamente!")
            self.dialogo_abierto = False
            await self.cargar_datos()
        else:
            yield rx.toast.error("Error al actualizar la dieta del animal en la base de datos.")
        yield


# --- Tokens de color semánticos centralizados ---
_card_bg    = styles.card_bg
_card_border = styles.card_border
_input_bg   = styles.input_bg
_text_main  = styles.text_main
_text_muted = styles.text_muted
_text_sub   = styles.text_sub
_info_bg    = styles.info_bg
_info_border = styles.info_border
_info_text  = styles.info_text
_info_body  = styles.info_body


def elemento_tabla_alimentacion(registro: rx.Var[list]) -> rx.Component:
    """Fila para cada animal en la tabla de dieta y alimentación con rangos ideales y semáforos."""
    return rx.table.row(
        rx.table.cell(registro[0].to_string(), color=_text_muted),
        rx.table.cell(registro[1], font_weight="bold", color=_text_main),
        rx.table.cell(registro[2], color=_text_sub),
        # Peso con rango ideal y semáforo
        rx.table.cell(
            rx.hstack(
                rx.text(
                    registro[3].to_string() + " kg",
                    font_weight="bold",
                    color=rx.cond(
                        registro[8] == "bueno",
                        rx.color_mode_cond(light="#059669", dark="#10b981"), # Verde
                        rx.cond(
                            registro[8] == "bajo",
                            rx.color_mode_cond(light="#d97706", dark="#f59e0b"), # Amber
                            rx.color_mode_cond(light="#2563eb", dark="#60a5fa")  # Azul (exceso)
                        )
                    )
                ),
                rx.text(
                    f"(Ideal: {registro[6]})",
                    font_size="0.75em",
                    color=_text_muted
                ),
                rx.badge(
                    rx.cond(registro[8] == "bueno", "Óptimo", rx.cond(registro[8] == "bajo", "Bajo Peso", "Sobrepeso")),
                    color_scheme=rx.cond(registro[8] == "bueno", "green", rx.cond(registro[8] == "bajo", "amber", "blue")),
                    variant="soft",
                    size="1"
                ),
                spacing="2",
                align_items="center"
            )
        ),
        # Consumo Diario con rango ideal y semáforo
        rx.table.cell(
            rx.hstack(
                rx.text(
                    registro[4].to_string() + " kg/día",
                    font_weight="bold",
                    color=rx.cond(
                        registro[9] == "bueno",
                        rx.color_mode_cond(light="#059669", dark="#10b981"), # Verde
                        rx.cond(
                            registro[9] == "bajo",
                            rx.color_mode_cond(light="#d97706", dark="#f59e0b"), # Amber
                            rx.color_mode_cond(light="#dc2626", dark="#f87171")  # Rojo (exceso costoso)
                        )
                    )
                ),
                rx.text(
                    f"(Ideal: {registro[7]}/día)",
                    font_size="0.75em",
                    color=_text_muted
                ),
                rx.badge(
                    rx.cond(registro[9] == "bueno", "Óptimo", rx.cond(registro[9] == "bajo", "Bajo", "Exceso")),
                    color_scheme=rx.cond(registro[9] == "bueno", "green", rx.cond(registro[9] == "bajo", "amber", "red")),
                    variant="soft",
                    size="1"
                ),
                spacing="2",
                align_items="center"
            )
        ),
        rx.table.cell(
            rx.badge(registro[5], color_scheme="orange", variant="soft")
        ),
        rx.table.cell(
            rx.button(
                "Asignar Dieta",
                on_click=lambda: AlimentacionState.abrir_editor_dieta(
                    registro[0].to(int),
                    registro[1].to(str),
                    registro[5].to(str)
                ),
                color_scheme="orange",
                size="1",
                variant="solid",
                cursor="pointer"
            )
        )
    )


def alimentacion_view() -> rx.Component:
    """Vista principal para la administración de Alimentación y Proyecciones Financieras."""
    return rx.vstack(
        # --- Cabecera e Indicadores de Costos ---
        rx.heading("Consumo de Alimento y Proyecciones Financieras del Rebaño", size="4", color=_text_main, margin_top="10px"),
        rx.grid(
            styles.kpi_card("Consumo Total", AlimentacionState.total_kg_fmt + " kg", subtitulo="Requerimiento diario global", icono="wheat", color_badge="#f59e0b"),
            styles.kpi_card("Costo Diario", "$" + AlimentacionState.costo_diario_fmt + " USD", subtitulo="Gasto diario de mantenimiento", icono="dollar-sign", color_badge="#10b981"),
            styles.kpi_card("Costo Mensual", "$" + AlimentacionState.costo_mensual_fmt + " USD", subtitulo="Proyección financiera a 30 días", icono="calendar", color_badge="#6366f1"),
            columns={"initial": "1", "sm": "3"},
            spacing="4",
            width="100%",
            margin_bottom="10px"
        ),

        # --- Notificaciones y Alertas ---

        # --- Área de Trabajo Principal ---
        rx.grid(
            # Columna Izquierda: Configuración Financiera
            rx.card(
                rx.vstack(
                    rx.heading("Parámetros Financieros", size="3", color=_text_main),
                    rx.text("Ajusta los costos unitarios del alimento para actualizar las proyecciones en tiempo real.", font_size="0.8em", color=_text_muted),

                    rx.text("Costo por Kilogramo ($ USD)", weight="bold", font_size="0.85em", color=_text_sub),
                    rx.input(
                        type="number",
                        min="0",
                        step="0.01",
                        placeholder="Ej. 0.50",
                        value=AlimentacionState.costo_por_kg,
                        on_change=AlimentacionState.cambiar_costo,
                        width="100%",
                        background_color=_input_bg,
                    ),

                    rx.box(
                        rx.hstack(
                            rx.icon("info", color=_info_text, size=18),
                            rx.text(
                                "Este costo se multiplica directamente por el consumo diario acumulado de cada animal activo en sus registros biométricos.",
                                font_size="0.76em",
                                color=_info_body,
                            ),
                            spacing="3",
                            align_items="start",
                        ),
                        background_color=_info_bg,
                        border=_info_border,
                        border_radius="8px",
                        padding="12px",
                        margin_top="10px",
                        width="100%",
                    ),
                    spacing="3",
                    align_items="start",
                ),
                background_color=_card_bg,
                border=_card_border,
                width="100%",
                padding="20px",
            ),

            # Columna Derecha: Tabla de Dieta de Animales Activos
            rx.card(
                rx.vstack(
                    rx.hstack(
                        rx.heading("Dietas y Consumos Individuales", size="3", color=_text_main),
                        rx.spacer(),
                        rx.input(
                            placeholder="Buscar...",
                            value=AlimentacionState.busqueda,
                            on_change=AlimentacionState.cambiar_busqueda,
                            size="1",
                            width="160px",
                            background_color=_input_bg,
                        ),
                        width="100%",
                        align_items="center",
                    ),
                    rx.text("Lista de animales activos y sus correspondientes raciones diarias de alimento.", font_size="0.8em", color=_text_muted, margin_bottom="10px"),

                    rx.box(
                        rx.table.root(
                            rx.table.header(
                                rx.table.row(
                                    rx.table.column_header_cell("ID", color=_text_muted),
                                    rx.table.column_header_cell("Código", color=_text_muted),
                                    rx.table.column_header_cell("Especie", color=_text_muted),
                                    rx.table.column_header_cell("Peso (Actual vs Ideal)", color=_text_muted),
                                    rx.table.column_header_cell("Consumo (Actual vs Ideal)", color=_text_muted),
                                    rx.table.column_header_cell("Dieta Asignada", color=_text_muted),
                                    rx.table.column_header_cell("Acción", color=_text_muted),
                                )
                            ),
                            rx.table.body(
                                rx.foreach(
                                    AlimentacionState.lista_detalle_alimentacion_filtrada,
                                    elemento_tabla_alimentacion
                                )
                            ),
                            width="100%",
                            variant="surface",
                        ),
                        overflow_x="auto",
                        width="100%",
                    ),
                    width="100%",
                ),
                background_color=_card_bg,
                border=_card_border,
                width="100%",
                padding="20px",
            ),
            grid_template_columns={"initial": "1fr", "lg": "350px 1fr"},
            spacing="4",
            width="100%",
            align_items="start",
        ),

        # --- Sección de Análisis Gráfico ---
        rx.card(
            rx.vstack(
                rx.hstack(
                    rx.icon("chart-bar", color="#10b981", size=22),
                    rx.heading("Análisis Gráfico de Consumo y Dietas", size="3", color=_text_main),
                    spacing="2",
                    align="center",
                ),
                rx.text(
                    "Visualiza la distribución de alimento y las dietas asignadas al rebaño en tiempo real.",
                    font_size="0.8em",
                    color=_text_muted,
                    margin_bottom="15px",
                ),
                rx.cond(
                    AlimentacionState.lista_detalle_alimentacion.length() == 0,
                    rx.center(
                        rx.text("No hay suficientes datos de animales activos para mostrar gráficas.", color=_text_muted, font_size="0.85em"),
                        width="100%",
                        padding_y="20px",
                    ),
                    rx.grid(
                        # Gráfica 1: Consumo diario por animal
                        rx.vstack(
                            rx.text("Consumo Diario de Alimento por Animal (kg/día)", font_size="0.85em", weight="bold", color=_text_sub, margin_bottom="10px"),
                            rx.recharts.responsive_container(
                                rx.recharts.bar_chart(
                                    rx.recharts.bar(
                                        rx.foreach(
                                            AlimentacionState.datos_grafica_consumo,
                                            lambda entry: rx.recharts.cell(fill=entry["fill"])
                                        ),
                                        data_key="consumo",
                                        radius=[4, 4, 0, 0],
                                    ),
                                    rx.recharts.x_axis(data_key="name", stroke=rx.color_mode_cond(light="#64748b", dark="#9ca3af"), font_size=10),
                                    rx.recharts.y_axis(stroke=rx.color_mode_cond(light="#64748b", dark="#9ca3af"), font_size=10),
                                    rx.recharts.cartesian_grid(stroke_dasharray="3 3", stroke=rx.color_mode_cond(light="#e2e8f0", dark="#374151")),
                                    rx.recharts.graphing_tooltip(),
                                    data=AlimentacionState.datos_grafica_consumo,
                                ),
                                width="99%",
                                height=260,
                            ),
                            align_items="center",
                            width="100%",
                        ),
                        # Gráfica 2: Distribución de dietas
                        rx.vstack(
                            rx.text("Distribución de Dietas en el Rebaño", font_size="0.85em", weight="bold", color=_text_sub, margin_bottom="10px"),
                            rx.recharts.responsive_container(
                                rx.recharts.pie_chart(
                                    rx.recharts.pie(
                                        data=AlimentacionState.datos_grafica_dietas,
                                        data_key="value",
                                        name_key="name",
                                        cx="50%",
                                        cy="50%",
                                        outer_radius=80,
                                        label=True,
                                    ),
                                    rx.recharts.graphing_tooltip(),
                                    rx.recharts.legend(vertical_align="bottom", height=36, font_size=10),
                                ),
                                width="99%",
                                height=260,
                            ),
                            align_items="center",
                            width="100%",
                        ),
                        columns={"initial": "1", "md": "2"},
                        spacing="6",
                        width="100%",
                    ),
                ),
                width="100%",
            ),
            background_color=_card_bg,
            border=_card_border,
            width="100%",
            padding="20px",
            margin_top="15px",
        ),

        # --- Modal para Asignar / Editar Dieta ---
        rx.dialog.root(
            rx.dialog.content(
                rx.vstack(
                    rx.dialog.title("Asignar Dieta a ", AlimentacionState.codigo_animal_seleccionado, color=_text_main),
                    rx.dialog.description(
                        "Especifique el tipo de alimento o régimen alimenticio (dieta) del animal.",
                        color=_text_muted,
                        font_size="0.85em"
                    ),
                    rx.text("Régimen de Alimentación / Dieta", weight="bold", font_size="0.85em", color=_text_sub, margin_top="10px"),
                    rx.input(
                        placeholder="Ej. Concentrado Proteico / Forraje Verde",
                        value=AlimentacionState.nuevo_tipo_alimento,
                        on_change=AlimentacionState.cambiar_nuevo_tipo_alimento,
                        width="100%",
                        background_color=_input_bg,
                        max_length=120,
                    ),
                    rx.hstack(
                        rx.dialog.close(
                            rx.button("Cancelar", variant="soft", color_scheme="gray", on_click=AlimentacionState.cerrar_editor_dieta, cursor="pointer")
                        ),
                        rx.button("Guardar Dieta", color_scheme="orange", on_click=AlimentacionState.guardar_dieta, cursor="pointer", loading=AlimentacionState.guardando),
                        spacing="3",
                        margin_top="15px",
                        width="100%",
                        justify="end"
                    ),
                    spacing="3",
                    align_items="start"
                ),
                max_width="450px",
                padding="20px"
            ),
            open=AlimentacionState.dialogo_abierto
        ),
        spacing="4",
        width="100%"
    )
