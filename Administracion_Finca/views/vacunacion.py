# Administracion_Finca/views/vacunacion.py
import reflex as rx
import backend_vacunacion
import backend_animales
from . import styles

class VacunacionState(rx.State):
    """Gestor de Estado modular para la sanidad y vacunación de la finca."""
    
    # --- Datos de la Jornada de Vacunación ---
    especie_seleccionada: str = "🐄 Bovino"
    nombre_vacuna_seleccionada: str = ""
    id_vacuna_seleccionada: int = 0
    catalogo_vacunas_nombres: list[str] = []
    map_vacuna_nombre_a_id: dict[str, int] = {}
    map_vacuna_nombre_a_retiro: dict[str, int] = {}
    
    nro_lote: str = ""
    laboratorio: str = ""
    veterinario: str = ""
    fecha_aplicacion: str = ""
    
    registrando: bool = False
    dias_retiro_seleccionado: int = 0
    
    # --- Selección de Animales ---
    lista_completa_animales: list[list] = []
    animales_seleccionados: list[int] = []
    busqueda_selector: str = ""
    busqueda_historial: str = ""

    # --- Historial y KPIs ---
    historial_vacunacion: list[list] = []
    alertas_sanitarias_count: int = 0
    total_aplicaciones: int = 0
    total_lotes: int = 0
    lista_alertas_sanitarias_codigos: list[str] = []

    async def cargar_datos(self):
        """Pobla los datos sanitarios y de animales desde el backend."""
        todos_animales = await rx.run_in_thread(backend_animales.obtener_lista_animales)
        self.lista_completa_animales = todos_animales
        
        historial = await rx.run_in_thread(backend_vacunacion.obtener_historial_vacunacion)
        self.historial_vacunacion = historial
        self.total_aplicaciones = len(historial)
        self.total_lotes = len(set(v[5] for v in historial if len(v) > 5 and v[5]))
        
        sanitarias = await rx.run_in_thread(backend_animales.obtener_alertas_sanitarias)
        self.alertas_sanitarias_count = sanitarias
        self.lista_alertas_sanitarias_codigos = await rx.run_in_thread(backend_animales.obtener_codigos_alertas_sanitarias)
        
        await self.cargar_vacunas_por_especie()

    async def cargar_vacunas_por_especie(self):
        """Carga del catálogo las vacunas permitidas para la especie actual."""
        especie_limpia = self.especie_seleccionada.replace("🐄 ", "").replace("🐖 ", "").replace("🐑 ", "").strip()
        id_esp = 1
        if especie_limpia == "Bovino": id_esp = 1
        elif especie_limpia == "Porcino": id_esp = 2
        elif especie_limpia == "Ovino": id_esp = 3
        
        def operacion_vacunas():
            return backend_vacunacion.obtener_vacunas_por_especie(id_esp)
            
        vacunas = await rx.run_in_thread(operacion_vacunas)
        
        self.map_vacuna_nombre_a_id = {v['nombre_enfermedad']: v['id_vacuna'] for v in vacunas}
        self.map_vacuna_nombre_a_retiro = {v['nombre_enfermedad']: v['dias_retiro'] for v in vacunas}
        self.catalogo_vacunas_nombres = list(self.map_vacuna_nombre_a_id.keys())
        
        if self.catalogo_vacunas_nombres:
            self.nombre_vacuna_seleccionada = self.catalogo_vacunas_nombres[0]
            self.id_vacuna_seleccionada = self.map_vacuna_nombre_a_id[self.nombre_vacuna_seleccionada]
            self.dias_retiro_seleccionado = self.map_vacuna_nombre_a_retiro.get(self.nombre_vacuna_seleccionada, 0)
        else:
            self.nombre_vacuna_seleccionada = ""
            self.id_vacuna_seleccionada = 0
            self.dias_retiro_seleccionado = 0

    async def cambiar_especie(self, valor: str):
        self.especie_seleccionada = valor
        self.animales_seleccionados = []
        await self.cargar_vacunas_por_especie()

    def cambiar_vacuna(self, valor: str):
        self.nombre_vacuna_seleccionada = valor
        self.id_vacuna_seleccionada = self.map_vacuna_nombre_a_id.get(valor, 0)
        self.dias_retiro_seleccionado = self.map_vacuna_nombre_a_retiro.get(valor, 0)

    def cambiar_nro_lote(self, valor: str):
        """Acepta solo alfanuméricos, guiones y guiones bajos. Máximo 30 caracteres."""
        import re
        sanitizado = re.sub(r"[^A-Za-z0-9\-_/]", "", valor).upper()
        self.nro_lote = sanitizado[:30]

    def cambiar_laboratorio(self, valor: str):
        """Acepta texto libre de hasta 80 caracteres. Elimina caracteres de control."""
        self.laboratorio = valor[:80].strip()

    def cambiar_veterinario(self, valor: str):
        """Acepta texto libre de hasta 80 caracteres. Elimina caracteres de control."""
        self.veterinario = valor[:80].strip()

    def cambiar_fecha_aplicacion(self, valor: str): self.fecha_aplicacion = valor

    def toggle_seleccion(self, id_animal: int):
        if id_animal in self.animales_seleccionados:
            self.animales_seleccionados.remove(id_animal)
        else:
            self.animales_seleccionados.append(id_animal)

    def seleccionar_todos(self):
        for a in self.lista_animales_especie:
            if len(a) > 0:
                anim_id = int(a[0])
                if anim_id not in self.animales_seleccionados:
                    self.animales_seleccionados.append(anim_id)

    def deseleccionar_todos(self):
        for a in self.lista_animales_especie:
            if len(a) > 0:
                anim_id = int(a[0])
                if anim_id in self.animales_seleccionados:
                    self.animales_seleccionados.remove(anim_id)

    def cambiar_busqueda_selector(self, valor: str):
        self.busqueda_selector = valor

    def cambiar_busqueda_historial(self, valor: str):
        self.busqueda_historial = valor

    @rx.var
    def historial_vacunacion_filtrado(self) -> list[list]:
        if self.busqueda_historial.strip() == "":
            return self.historial_vacunacion
        termino = self.busqueda_historial.strip().lower()
        return [
            row for row in self.historial_vacunacion
            if (termino in str(row[0]).lower()) or (termino in str(row[1]).lower())
        ]

    @rx.var
    def lista_animales_especie(self) -> list[list]:
        especie_limpia = self.especie_seleccionada.replace("🐄 ", "").replace("🐖 ", "").replace("🐑 ", "").strip()
        return [a for a in self.lista_completa_animales if len(a) > 2 and a[2] == especie_limpia]

    @rx.var
    def animales_con_seleccion(self) -> list[dict]:
        res = []
        termino = self.busqueda_selector.strip().lower()
        for a in self.lista_animales_especie:
            anim_id = int(a[0])
            codigo = a[1]
            if termino != "" and not (termino in str(anim_id).lower() or termino in str(codigo).lower()):
                continue
            is_sel = anim_id in self.animales_seleccionados
            res.append({
                "id": anim_id,
                "codigo": codigo,
                "categoria": a[5],
                "sexo": a[4],
                "seleccionado": is_sel
            })
        return res

    @rx.var
    def semaforo_sanitario(self) -> str:
        if self.alertas_sanitarias_count > 5: return "rojo"
        elif self.alertas_sanitarias_count > 0: return "amarillo"
        return "verde"

    async def registrar_jornada(self):
        if not self.id_vacuna_seleccionada:
            yield rx.toast.error("Error: Por favor, elija una vacuna válida del catálogo.")
            return
        if not self.nro_lote or not self.laboratorio or not self.veterinario or not self.fecha_aplicacion:
            yield rx.toast.error("Por favor, complete todos los campos informativos de la vacuna.")
            return
        # Validaciones de longitud mínima en campos de texto
        if len(self.laboratorio.strip()) < 2:
            yield rx.toast.warning("El nombre del laboratorio debe tener al menos 2 caracteres.")
            return
        if len(self.veterinario.strip()) < 2:
            yield rx.toast.warning("El nombre del veterinario debe tener al menos 2 caracteres.")
            return
        if not self.animales_seleccionados:
            yield rx.toast.error("Error: Debe seleccionar al menos un animal de la tabla para aplicar la vacuna.")
            return

        self.registrando = True
        yield

        def operacion_bd():
            return backend_vacunacion.registrar_vacunacion_lote(
                list(self.animales_seleccionados),
                self.id_vacuna_seleccionada,
                self.nro_lote.strip(),
                self.laboratorio.strip(),
                self.veterinario.strip(),
                self.fecha_aplicacion
            )

        try:
            exito, msg = await rx.run_in_thread(operacion_bd)
            if exito:
                yield rx.toast.success(msg)
                self.nro_lote = ""
                self.laboratorio = ""
                self.veterinario = ""
                self.fecha_aplicacion = ""
                self.animales_seleccionados = []
                await self.cargar_datos()
                await self._actualizar_otros_estados()
            else:
                yield rx.toast.error(msg)
        except Exception as error:
            print(f"Error al registrar vacuna: {error}")
            yield rx.toast.error(f"Error al registrar vacuna: {str(error)}")
        finally:
            self.registrando = False
            yield

    async def _actualizar_otros_estados(self):
        """Actualiza los datos en los otros gestores de estado modular."""
        try:
            from Administracion_Finca.views.animales import AnimalesState
            from Administracion_Finca.views.ia import IAState
            
            anim_state = await self.get_state(AnimalesState)
            await anim_state.cargar_datos()
            
            ia_state = await self.get_state(IAState)
            await ia_state.cargar_datos()
        except Exception as e:
            print(f"Error al actualizar otros estados desde VacunacionState: {e}")



# --- Tokens de color semánticos centralizados ---
_card_bg    = styles.card_bg
_card_border = styles.card_border
_input_bg   = styles.input_bg
_text_main  = styles.text_main
_text_muted = styles.text_muted
_text_sub   = styles.text_sub


def elemento_tabla_seleccion(animal: rx.Var[dict]) -> rx.Component:
    """Fila de selección de animal para vacunación."""
    return rx.table.row(
        rx.table.cell(animal["id"].to_string(), color=_text_muted),
        rx.table.cell(
            rx.hstack(
                rx.text(animal["codigo"], font_weight="bold", color=_text_main),
                rx.cond(
                    VacunacionState.lista_alertas_sanitarias_codigos.contains(animal["codigo"]),
                    rx.badge("⚠️ Alerta", color_scheme="red", variant="solid")
                ),
                spacing="2",
                align="center"
            )
        ),
        rx.table.cell(
            rx.badge(
                animal["sexo"],
                color_scheme=rx.cond(animal["sexo"] == "M", "blue", "pink"),
                variant="soft"
            )
        ),
        rx.table.cell(rx.badge(animal["categoria"], color_scheme="teal")),
        rx.table.cell(
            rx.cond(
                animal["seleccionado"],
                rx.button(
                    "Seleccionado",
                    on_click=lambda: VacunacionState.toggle_seleccion(animal["id"]),
                    color_scheme="green",
                    size="1"
                ),
                rx.button(
                    "Seleccionar",
                    on_click=lambda: VacunacionState.toggle_seleccion(animal["id"]),
                    color_scheme="gray",
                    size="1",
                    variant="outline"
                )
            )
        )
    )


def elemento_tabla_historial(vacuna: rx.Var[list]) -> rx.Component:
    """Fila para la tabla de historial de vacunaciones aplicadas."""
    return rx.table.row(
        rx.table.cell(vacuna[0].to_string(), color=_text_muted),
        rx.table.cell(vacuna[1], font_weight="bold", color=_text_main),
        rx.table.cell(vacuna[2], color=rx.color_mode_cond(light="#1d4ed8", dark="#60a5fa")),
        rx.table.cell(vacuna[3], color=_text_sub),
        rx.table.cell(
            rx.cond(
                vacuna[4] != "",
                rx.badge(vacuna[4], color_scheme="purple", variant="solid"),
                rx.badge("Dosis Única", color_scheme="gray")
            )
        ),
        rx.table.cell(vacuna[5], color=_text_sub),
        rx.table.cell(vacuna[6], color=_text_sub),
        rx.table.cell(vacuna[7], color=_text_muted)
    )


def vacunacion_view() -> rx.Component:
    """Vista principal para el control de Sanidad y Campañas de Vacunación."""
    return rx.vstack(
        # --- Cabecera y KPIs Sanitarios ---
        rx.heading("Estatus Sanitario y Campañas Colectivas", size="4", color=_text_main, margin_top="10px"),
        rx.grid(
            styles.kpi_card("Controles Aplicados", VacunacionState.total_aplicaciones.to_string(), estado="verde", subtitulo="Historial total dosis aplicadas"),
            styles.kpi_card("Lotes Biológicos", VacunacionState.total_lotes.to_string(), estado="verde", subtitulo="Lotes comerciales trazados"),
            styles.kpi_card(
                "Alertas Sanitarias", 
                VacunacionState.alertas_sanitarias_count.to_string(), 
                estado=VacunacionState.semaforo_sanitario, 
                subtitulo="Cabezas con dosis vencida",
                popover_content=rx.cond(
                    VacunacionState.alertas_sanitarias_count > 0,
                    rx.vstack(
                        rx.text("Animales con dosis vencida:", font_size="0.8em", weight="bold", color=_text_main),
                        rx.flex(
                            rx.foreach(
                                VacunacionState.lista_alertas_sanitarias_codigos,
                                lambda c: rx.badge(c, color_scheme="red", variant="solid", margin="2px")
                            ),
                            flex_wrap="wrap",
                            max_width="200px"
                        ),
                        spacing="2",
                        align="start",
                        padding="8px"
                    ),
                    rx.text("No hay alertas activas", font_size="0.8em", color=_text_muted, padding="8px")
                )
            ),
            columns={"initial": "1", "sm": "3"},
            spacing="4",
            width="100%",
            margin_bottom="10px"
        ),

        # --- Alertas ---

        # --- Área de Trabajo ---
        rx.flex(
            # Columna Izquierda: Formulario
            rx.card(
                rx.vstack(
                    rx.heading("Registrar Jornada de Vacunación", size="3", color=_text_main),
                    rx.text("Registra la aplicación de vacunas en lote para la trazabilidad oficial del INSAI", font_size="0.8em", color=_text_muted),

                    rx.flex(
                        rx.vstack(
                            rx.text("Especie Destino", weight="bold", font_size="0.85em", color=_text_sub),
                            rx.select(
                                ["🐄 Bovino", "🐖 Porcino", "🐑 Ovino"],
                                value=VacunacionState.especie_seleccionada,
                                on_change=VacunacionState.cambiar_especie,
                                width="100%",
                            ),
                            align_items="start", width={"initial": "100%", "sm": "50%"}
                        ),
                        rx.vstack(
                            rx.text("Vacuna (Catálogo INSAI)", weight="bold", font_size="0.85em", color=_text_sub),
                            rx.select(
                                VacunacionState.catalogo_vacunas_nombres,
                                value=VacunacionState.nombre_vacuna_seleccionada,
                                on_change=VacunacionState.cambiar_vacuna,
                                width="100%",
                            ),
                            align_items="start", width={"initial": "100%", "sm": "50%"}
                        ),
                        width="100%",
                        direction={"initial": "column", "sm": "row"},
                        spacing="3"
                    ),
                    # Alerta de Período de Retiro
                    rx.cond(
                        VacunacionState.dias_retiro_seleccionado > 0,
                        rx.hstack(
                            rx.icon("info", color="#fbbf24", size=16),
                            rx.text(
                                "Período de retiro: ",
                                VacunacionState.dias_retiro_seleccionado,
                                " días. No destinar leche/carne a consumo humano.",
                                font_size="0.75em",
                                color="#fb923c",
                                weight="bold"
                            ),
                            spacing="1",
                            align="center",
                            margin_top="-2px"
                        )
                    ),

                    rx.flex(
                        rx.vstack(
                            rx.text("Lote Comercial", weight="bold", font_size="0.85em", color=_text_sub),
                            rx.input(
                                placeholder="Ej. LOT-AFF-40",
                                value=VacunacionState.nro_lote,
                                on_change=VacunacionState.cambiar_nro_lote,
                                width="100%",
                                background_color=_input_bg,
                            ),
                            align_items="start", width={"initial": "100%", "sm": "50%"}
                        ),
                        rx.vstack(
                            rx.text("Fecha de Aplicación", weight="bold", font_size="0.85em", color=_text_sub),
                            rx.input(
                                type="date",
                                value=VacunacionState.fecha_aplicacion,
                                on_change=VacunacionState.cambiar_fecha_aplicacion,
                                width="100%",
                                background_color=_input_bg,
                            ),
                            align_items="start", width={"initial": "100%", "sm": "50%"}
                        ),
                        width="100%",
                        direction={"initial": "column", "sm": "row"},
                        spacing="3"
                    ),

                    rx.flex(
                        rx.vstack(
                            rx.text("Laboratorio", weight="bold", font_size="0.85em", color=_text_sub),
                            rx.input(placeholder="Ej. Bayer", value=VacunacionState.laboratorio, on_change=VacunacionState.cambiar_laboratorio, width="100%", background_color=_input_bg),
                            align_items="start", width={"initial": "100%", "sm": "50%"}
                        ),
                        rx.vstack(
                            rx.text("Veterinario", weight="bold", font_size="0.85em", color=_text_sub),
                            rx.input(placeholder="Ej. Dr. Pérez", value=VacunacionState.veterinario, on_change=VacunacionState.cambiar_veterinario, width="100%", background_color=_input_bg),
                            align_items="start", width={"initial": "100%", "sm": "50%"}
                        ),
                        width="100%",
                        direction={"initial": "column", "sm": "row"},
                        spacing="3"
                    ),

                    rx.button(
                        "Registrar Jornada Veterinaria",
                        on_click=VacunacionState.registrar_jornada,
                        color_scheme="green",
                        width="100%",
                        margin_top="10px",
                        cursor="pointer",
                        loading=VacunacionState.registrando,
                    ),
                    spacing="3",
                    align_items="start",
                ),
                background_color=_card_bg,
                border=_card_border,
                width={"initial": "100%", "lg": "380px"},
                padding="20px",
            ),

            # Columna Derecha: Selector de Animales
            rx.card(
                rx.vstack(
                    rx.heading("Seleccionar Animales del Lote", size="3", color=_text_main),
                    rx.text(
                        "Muestra los animales activos de tipo '",
                        VacunacionState.especie_seleccionada,
                        "'. Selecciona los ejemplares vacunados.",
                        font_size="0.8em",
                        color=_text_muted,
                        margin_bottom="10px"
                    ),
                    rx.hstack(
                        rx.button("Seleccionar Todos", on_click=VacunacionState.seleccionar_todos, color_scheme="blue", variant="soft", size="1", cursor="pointer"),
                        rx.button("Deseleccionar Todos", on_click=VacunacionState.deseleccionar_todos, color_scheme="gray", variant="soft", size="1", cursor="pointer"),
                        rx.spacer(),
                        rx.input(
                            placeholder="Buscar...",
                            value=VacunacionState.busqueda_selector,
                            on_change=VacunacionState.cambiar_busqueda_selector,
                            size="1",
                            width="160px",
                            background_color=_input_bg,
                        ),
                        spacing="2",
                        margin_bottom="10px",
                        width="100%",
                        align_items="center",
                    ),
                    rx.box(
                        rx.table.root(
                            rx.table.header(
                                rx.table.row(
                                    rx.table.column_header_cell("ID", color=_text_muted),
                                    rx.table.column_header_cell("Código", color=_text_muted),
                                    rx.table.column_header_cell("Sexo", color=_text_muted),
                                    rx.table.column_header_cell("Categoría", color=_text_muted),
                                    rx.table.column_header_cell("Acción", color=_text_muted),
                                )
                            ),
                            rx.table.body(
                                rx.foreach(
                                    VacunacionState.animales_con_seleccion,
                                    elemento_tabla_seleccion
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
                flex="1",
                width="100%",
                padding="20px",
            ),
            width="100%",
            align_items="start",
            spacing="4",
            direction={"initial": "column", "lg": "row"},
        ),

        # --- Historial de Vacunación ---
        rx.card(
            rx.vstack(
                rx.hstack(
                    rx.heading("Histórico de Aplicaciones Veterinarias", size="3", color=_text_main),
                    rx.spacer(),
                    rx.input(
                        placeholder="Buscar por código/registro...",
                        value=VacunacionState.busqueda_historial,
                        on_change=VacunacionState.cambiar_busqueda_historial,
                        size="1",
                        width="200px",
                        background_color=_input_bg,
                    ),
                    width="100%",
                    align_items="center",
                    margin_bottom="10px",
                ),
                rx.box(
                    rx.table.root(
                        rx.table.header(
                            rx.table.row(
                                rx.table.column_header_cell("Reg", color=_text_muted),
                                rx.table.column_header_cell("Animal", color=_text_muted),
                                rx.table.column_header_cell("Vacuna / Enfermedad", color=_text_muted),
                                rx.table.column_header_cell("Aplicación", color=_text_muted),
                                rx.table.column_header_cell("Próxima Agenda", color=_text_muted),
                                rx.table.column_header_cell("Lote Comercial", color=_text_muted),
                                rx.table.column_header_cell("Laboratorio", color=_text_muted),
                                rx.table.column_header_cell("Veterinario", color=_text_muted),
                            )
                        ),
                        rx.table.body(
                            rx.foreach(
                                VacunacionState.historial_vacunacion_filtrado,
                                elemento_tabla_historial
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
            margin_top="10px",
        ),
        spacing="4",
        width="100%"
    )
