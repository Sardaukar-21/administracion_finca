# Administracion_Finca/views/animales.py
import reflex as rx
import re
import backend_animales
from . import styles

class AnimalesState(rx.State):
    """Gestor de Estado modular para la vista de Animales."""
    
    # --- Campos del Formulario de Registro ---
    numero_id: str = ""
    especie_nombre: str = "🐄 Bovino"
    sexo: str = "F"
    fecha_nacimiento: str = ""
    peso_inicial: str = ""
    alimento_inicial: str = ""
    registrando: bool = False

    # --- KPIs y Contadores ---
    total_animales: int = 0
    bovinos_count: int = 0
    porcinos_count: int = 0
    ovinos_count: int = 0
    alertas_sanitarias_count: int = 0
    alertas_produccion_count: int = 0
    lista_alertas_sanitarias_codigos: list[str] = []
    lista_alertas_produccion_codigos: list[str] = []

    # --- Inventario ---
    lista_completa_animales: list[list] = []
    especie_filtro: str = "📋 Todas"
    busqueda: str = ""

    # --- Modal de Confirmación de Baja ---
    dialogo_baja_abierto: bool = False
    baja_id_animal_pendiente: int = 0
    baja_estado_pendiente: int = 0   # 2 = Muerte, 3 = Venta
    baja_codigo_pendiente: str = ""

    async def cargar_datos(self):
        """Consulta los datos del backend en hilos secundarios para poblar la UI."""
        total = await rx.run_in_thread(backend_animales.obtener_total_animales)
        conteo_especie = await rx.run_in_thread(backend_animales.obtener_conteo_por_especie)
        sanitarias = await rx.run_in_thread(backend_animales.obtener_alertas_sanitarias)
        produccion = await rx.run_in_thread(backend_animales.obtener_alertas_produccion)
        dataset = await rx.run_in_thread(backend_animales.obtener_lista_animales)

        self.total_animales = total
        self.bovinos_count = conteo_especie.get("Bovino", 0)
        self.porcinos_count = conteo_especie.get("Porcino", 0)
        self.ovinos_count = conteo_especie.get("Ovino", 0)
        self.alertas_sanitarias_count = sanitarias
        self.alertas_produccion_count = produccion
        self.lista_completa_animales = dataset
        self.lista_alertas_sanitarias_codigos = await rx.run_in_thread(backend_animales.obtener_codigos_alertas_sanitarias)
        self.lista_alertas_produccion_codigos = await rx.run_in_thread(backend_animales.obtener_codigos_alertas_produccion)

    def cambiar_numero_id(self, valor: str):
        """Acepta solo códigos alfanuméricos, guiones y guiones bajos. Máximo 20 caracteres."""
        sanitizado = re.sub(r"[^A-Za-z0-9\-_]", "", valor).upper()
        self.numero_id = sanitizado[:20]

    def cambiar_especie(self, valor: str):
        self.especie_nombre = valor

    def cambiar_sexo(self, valor: str):
        self.sexo = valor

    def cambiar_fecha_nacimiento(self, valor: str):
        self.fecha_nacimiento = valor

    def cambiar_peso(self, valor: str):
        """Valida que el peso inicial sea un decimal válido (ej. 350.50)."""
        if valor == "":
            self.peso_inicial = ""
            return
        patron = r"^\d*\.?\d{0,2}$"
        if re.match(patron, valor):
            self.peso_inicial = valor

    def cambiar_alimento(self, valor: str):
        """Valida que el consumo de alimento diario sea un decimal válido."""
        if valor == "":
            self.alimento_inicial = ""
            return
        patron = r"^\d*\.?\d{0,2}$"
        if re.match(patron, valor):
            self.alimento_inicial = valor

    def cambiar_filtro(self, valor: str):
        self.especie_filtro = valor

    def cambiar_busqueda(self, valor: str):
        self.busqueda = valor

    @rx.var
    def animales_filtrados(self) -> list[list]:
        filtro_limpio = self.especie_filtro.replace("📋 ", "").replace("🐄 ", "").replace("🐖 ", "").replace("🐑 ", "").replace("⚠️ ", "").strip()
        if filtro_limpio == "Todas":
            lista = self.lista_completa_animales
        elif filtro_limpio == "Con Alertas":
            lista = [
                a for a in self.lista_completa_animales 
                if len(a) > 1 and (
                    a[1] in self.lista_alertas_sanitarias_codigos or 
                    a[1] in self.lista_alertas_produccion_codigos
                )
            ]
        else:
            lista = [a for a in self.lista_completa_animales if len(a) > 2 and a[2] == filtro_limpio]
            
        if self.busqueda.strip() != "":
            termino = self.busqueda.strip().lower()
            lista = [
                a for a in lista
                if (termino in str(a[0]).lower()) or (termino in str(a[1]).lower())
            ]
        return lista

    # --- Semáforos de KPIs ---
    @rx.var
    def semaforo_inventario(self) -> str:
        if self.total_animales < 5: return "rojo"
        elif self.total_animales < 15: return "amarillo"
        return "verde"

    @rx.var
    def semaforo_sanitario(self) -> str:
        if self.alertas_sanitarias_count > 5: return "rojo"
        elif self.alertas_sanitarias_count > 0: return "amarillo"
        return "verde"

    @rx.var
    def semaforo_produccion(self) -> str:
        if self.alertas_produccion_count > 3: return "rojo"
        elif self.alertas_produccion_count > 0: return "amarillo"
        return "verde"

    async def registrar_nuevo_animal(self):
        """Registra un animal con su peso e ingesta de alimento inicial utilizando transacciones en el backend."""
        # Validación de campos
        if not self.numero_id or not self.fecha_nacimiento or not self.peso_inicial or not self.alimento_inicial:
            yield rx.toast.warning("Todos los campos son obligatorios para el registro inicial.")
            return

        # Evitar puntos flotantes inválidos
        if self.peso_inicial.endswith('.') or self.alimento_inicial.endswith('.'):
            yield rx.toast.warning("Por favor, complete los valores decimales.")
            return

        # --- Validaciones de seguridad y formato ---
        # Verificar que el código sea alfanumérico (sin caracteres especiales ni scripts)
        if not re.match(r'^[A-Z0-9\-_]{2,20}$', self.numero_id):
            yield rx.toast.warning("El código del animal solo admite letras, números, guiones y guiones bajos (2–20 car.)")
            return

        # Evitar iniciales cruzadas que causen confusión de especies
        especie_limpia = self.especie_nombre.replace("🐄 ", "").replace("🐖 ", "").replace("🐑 ", "").strip()
        codigo_upper = self.numero_id.upper()
        if especie_limpia == "Bovino":
            if "OVI" in codigo_upper or "POR" in codigo_upper:
                yield rx.toast.warning("Para un Bovino, el código no puede contener iniciales de otras especies ('OVI' o 'POR').")
                return
        elif especie_limpia == "Porcino":
            if "BOV" in codigo_upper or "OVI" in codigo_upper:
                yield rx.toast.warning("Para un Porcino, el código no puede contener iniciales de otras especies ('BOV' o 'OVI').")
                return
        elif especie_limpia == "Ovino":
            if "BOV" in codigo_upper or "POR" in codigo_upper:
                yield rx.toast.warning("Para un Ovino, el código no puede contener iniciales de otras especies ('BOV' o 'POR').")
                return

        # Verificar rango sensato de valores numéricos (evitar valores absurdos)
        try:
            peso_val = float(self.peso_inicial)
            alimento_val = float(self.alimento_inicial)
        except ValueError:
            yield rx.toast.error("Los valores de Peso o Alimento no son números válidos.")
            return

        if not (1.0 <= peso_val <= 2000.0):
            yield rx.toast.warning("El peso inicial debe estar entre 1 y 2,000 kg.")
            return
        if not (0.1 <= alimento_val <= 200.0):
            yield rx.toast.warning("El consumo diario debe estar entre 0.1 y 200 kg/día.")
            return

        self.registrando = True
        yield

        especie_limpia = self.especie_nombre.replace("🐄 ", "").replace("🐖 ", "").replace("🐑 ", "").strip()
        def operacion_bd():
            return backend_animales.registrar_animal_completo(
                self.numero_id.strip(),
                especie_limpia,
                self.sexo,
                self.fecha_nacimiento,
                peso_val,
                alimento_val
            )

        try:
            exito, msg = await rx.run_in_thread(operacion_bd)
            if exito:
                yield rx.toast.success(msg)
                self.numero_id = ""
                self.fecha_nacimiento = ""
                self.peso_inicial = ""
                self.alimento_inicial = ""
                await self.cargar_datos()
                await self._actualizar_otros_estados()
            else:
                yield rx.toast.error(msg)
        except Exception as error:
            print(f"Error en registro: {error}")
            yield rx.toast.error(f"Error en registro: {str(error)}")
        finally:
            self.registrando = False
            yield

    def solicitar_baja_animal(self, id_animal: int, estado: int, codigo: str):
        """Abre el diálogo de confirmación antes de ejecutar la baja."""
        self.baja_id_animal_pendiente = id_animal
        self.baja_estado_pendiente = estado
        self.baja_codigo_pendiente = codigo
        self.dialogo_baja_abierto = True

    def cancelar_baja(self):
        """Cierra el diálogo de confirmación sin realizar cambios."""
        self.dialogo_baja_abierto = False
        self.baja_id_animal_pendiente = 0
        self.baja_estado_pendiente = 0
        self.baja_codigo_pendiente = ""

    async def confirmar_baja_animal(self):
        """Ejecuta la baja del animal confirmada en el diálogo."""
        self.dialogo_baja_abierto = False
        id_animal = self.baja_id_animal_pendiente
        estado = self.baja_estado_pendiente

        def operacion_bd():
            # 2: Muerto, 3: Vendido
            exito, msg = backend_animales.actualizar_estado_animal(id_animal, estado)
            return exito, msg

        exito, msg = await rx.run_in_thread(operacion_bd)
        if exito:
            tipo = "fallecido" if estado == 2 else "vendido"
            yield rx.toast.success(f"Animal {self.baja_codigo_pendiente} registrado como {tipo} exitosamente.")
            self.baja_id_animal_pendiente = 0
            self.baja_estado_pendiente = 0
            self.baja_codigo_pendiente = ""
            await self.cargar_datos()
            await self._actualizar_otros_estados()
        else:
            yield rx.toast.error(f"Fallo al dar de baja: {msg}")

    async def _actualizar_otros_estados(self):
        """Actualiza los datos en los otros gestores de estado modular."""
        try:
            from Administracion_Finca.views.vacunacion import VacunacionState
            from Administracion_Finca.views.alimentacion import AlimentacionState
            from Administracion_Finca.views.ia import IAState
            
            vac_state = await self.get_state(VacunacionState)
            await vac_state.cargar_datos()
            
            alim_state = await self.get_state(AlimentacionState)
            await alim_state.cargar_datos()
            
            ia_state = await self.get_state(IAState)
            await ia_state.cargar_datos()
        except Exception as e:
            print(f"Error al actualizar otros estados desde AnimalesState: {e}")



# --- Tokens de color semánticos (importados de styles) ---
_card_bg = styles.card_bg
_card_border = styles.card_border
_input_bg = styles.input_bg
_text_main = styles.text_main
_text_muted = styles.text_muted
_text_sub = styles.text_sub
_text_accent = styles.text_accent

from .styles import kpi_card


def elemento_tabla_animal(animal: rx.Var[list]) -> rx.Component:
    """Fila para cada animal en la tabla de inventario general."""
    return rx.table.row(
        rx.table.cell(animal[0].to_string(), color=_text_muted),
        rx.table.cell(
            rx.hstack(
                rx.text(animal[1], font_weight="bold", color=_text_main),
                rx.cond(
                    AnimalesState.lista_alertas_sanitarias_codigos.contains(animal[1]),
                    rx.badge("⚕️ Sanitaria", color_scheme="red", variant="solid")
                ),
                rx.cond(
                    AnimalesState.lista_alertas_produccion_codigos.contains(animal[1]),
                    rx.badge("⚠️ Alerta", color_scheme="amber", variant="solid")
                ),
                spacing="2",
                align="center"
            )
        ),
        rx.table.cell(animal[2], color=_text_sub),
        rx.table.cell(
            rx.badge(
                animal[4],
                color_scheme=rx.cond(animal[4] == "M", "blue", "pink"),
                variant="soft"
            )
        ),
        rx.table.cell(
            rx.badge(animal[5], color_scheme="teal", variant="solid")
        ),
        rx.table.cell(animal[3], color=_text_muted),
        rx.table.cell(
            rx.hstack(
                rx.tooltip(
                    rx.button(
                        rx.icon("skull", size=13),
                        "Muerte",
                        on_click=lambda: AnimalesState.solicitar_baja_animal(
                            animal[0].to(int), 2, animal[1].to(str)
                        ),
                        color_scheme="red",
                        size="1",
                        variant="solid",
                        cursor="pointer",
                    ),
                    content="Registrar como fallecido",
                ),
                rx.tooltip(
                    rx.button(
                        rx.icon("badge-dollar-sign", size=13),
                        "Venta",
                        on_click=lambda: AnimalesState.solicitar_baja_animal(
                            animal[0].to(int), 3, animal[1].to(str)
                        ),
                        color_scheme="orange",
                        size="1",
                        variant="solid",
                        cursor="pointer",
                    ),
                    content="Registrar como vendido",
                ),
                spacing="2"
            )
        )
    )


def animales_view() -> rx.Component:
    """Vista principal para la administración de Animales de la finca."""
    return rx.vstack(
        # --- Cabecera de KPIs ---
        rx.heading("Control de Inventario y KPIs Sanitarios", size="4", color=_text_main, margin_top="10px"),
        rx.grid(
            kpi_card("Inventario Activo", AnimalesState.total_animales.to_string(), estado=AnimalesState.semaforo_inventario, subtitulo="Total cabezas activas"),
            kpi_card(
                "Alertas Sanitarias", 
                AnimalesState.alertas_sanitarias_count.to_string(), 
                estado=AnimalesState.semaforo_sanitario, 
                subtitulo="Control vacunas vencido",
                popover_content=rx.cond(
                    AnimalesState.alertas_sanitarias_count > 0,
                    rx.vstack(
                        rx.text("Animales con dosis vencida:", font_size="0.8em", weight="bold", color=_text_main),
                        rx.flex(
                            rx.foreach(
                                AnimalesState.lista_alertas_sanitarias_codigos,
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
            kpi_card(
                "Alertas Producción", 
                AnimalesState.alertas_produccion_count.to_string(), 
                estado=AnimalesState.semaforo_produccion, 
                subtitulo="Fuera del rango esperado",
                popover_content=rx.cond(
                    AnimalesState.alertas_produccion_count > 0,
                    rx.vstack(
                        rx.text("Animales fuera de rango:", font_size="0.8em", weight="bold", color=_text_main),
                        rx.flex(
                            rx.foreach(
                                AnimalesState.lista_alertas_produccion_codigos,
                                lambda c: rx.badge(c, color_scheme="amber", variant="solid", margin="2px")
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

        # --- Sección Principal de Trabajo (Registro y Tabla) ---
        rx.flex(
            # Columna izquierda: Registro de ejemplar
            rx.card(
                rx.vstack(
                    rx.heading("Alta Única de Animales", size="3", color=_text_main),
                    rx.text("Inicialización completa con métricas biométricas", font_size="0.8em", color=_text_muted),

                    rx.text("Código Identificación Único", weight="bold", font_size="0.85em", color=_text_sub),
                    rx.input(
                        placeholder="Ej. BOV-4021",
                        value=AnimalesState.numero_id,
                        on_change=AnimalesState.cambiar_numero_id,
                        width="100%",
                        background_color=_input_bg,
                        max_length=20,
                    ),

                    rx.flex(
                        rx.vstack(
                            rx.text("Especie", weight="bold", font_size="0.85em", color=_text_sub),
                            rx.select(["🐄 Bovino", "🐖 Porcino", "🐑 Ovino"], value=AnimalesState.especie_nombre, on_change=AnimalesState.cambiar_especie, width="100%"),
                            align_items="start", width={"initial": "100%", "sm": "50%"}
                        ),
                        rx.vstack(
                            rx.text("Sexo", weight="bold", font_size="0.85em", color=_text_sub),
                            rx.select(["F", "M"], value=AnimalesState.sexo, on_change=AnimalesState.cambiar_sexo, width="100%"),
                            align_items="start", width={"initial": "100%", "sm": "50%"}
                        ),
                        width="100%",
                        direction={"initial": "column", "sm": "row"},
                        spacing="3"
                    ),

                    rx.text("Fecha de Nacimiento", weight="bold", font_size="0.85em", color=_text_sub),
                    rx.input(
                        type="date",
                        value=AnimalesState.fecha_nacimiento,
                        on_change=AnimalesState.cambiar_fecha_nacimiento,
                        width="100%",
                        background_color=_input_bg,
                    ),

                    rx.flex(
                        rx.vstack(
                            rx.text("Peso Entrada (Kg)", weight="bold", font_size="0.85em", color=_text_sub),
                            rx.input(placeholder="Ej. 350.50", value=AnimalesState.peso_inicial, on_change=AnimalesState.cambiar_peso, width="100%", background_color=_input_bg),
                            align_items="start", width={"initial": "100%", "sm": "50%"}
                        ),
                        rx.vstack(
                            rx.text("Alimento Inicial (Kg/día)", weight="bold", font_size="0.85em", color=_text_sub),
                            rx.input(placeholder="Ej. 6.20", value=AnimalesState.alimento_inicial, on_change=AnimalesState.cambiar_alimento, width="100%", background_color=_input_bg),
                            align_items="start", width={"initial": "100%", "sm": "50%"}
                        ),
                        width="100%",
                        direction={"initial": "column", "sm": "row"},
                        spacing="3"
                    ),

                    rx.button(
                        "Registrar e Inicializar Animal",
                        on_click=AnimalesState.registrar_nuevo_animal,
                        color_scheme="green",
                        width="100%",
                        margin_top="10px",
                        loading=AnimalesState.registrando,
                    ),
                    spacing="3",
                    align_items="start",
                ),
                background_color=_card_bg,
                border=rx.color_mode_cond(light="1px solid #e2e8f0", dark="1px solid #374151"),
                width={"initial": "100%", "lg": "380px"},
                padding="20px",
            ),

            # Columna derecha: Inventario general de animales activos
            rx.card(
                rx.vstack(
                    rx.hstack(
                        rx.heading("Inventario Activo", size="3", color=_text_main),
                        rx.spacer(),
                        rx.hstack(
                            rx.badge("🐄 ", AnimalesState.bovinos_count, color_scheme="blue", variant="soft", size="1"),
                            rx.badge("🐖 ", AnimalesState.porcinos_count, color_scheme="orange", variant="soft", size="1"),
                            rx.badge("🐑 ", AnimalesState.ovinos_count, color_scheme="green", variant="soft", size="1"),
                            spacing="2",
                            display=["none", "flex", "flex"],
                        ),
                        rx.spacer(),
                        rx.input(
                            placeholder="Buscar...",
                            value=AnimalesState.busqueda,
                            on_change=AnimalesState.cambiar_busqueda,
                            size="1",
                            width="160px",
                            background_color=_input_bg,
                        ),
                        rx.select(
                            ["📋 Todas", "🐄 Bovino", "🐖 Porcino", "🐑 Ovino", "⚠️ Con Alertas"],
                            value=AnimalesState.especie_filtro,
                            on_change=AnimalesState.cambiar_filtro,
                            size="1"
                        ),
                        width="100%",
                        align_items="center"
                    ),
                    rx.text("Manejo zootécnico y control de bajas en tiempo real", font_size="0.8em", color=_text_muted, margin_bottom="10px"),

                    rx.cond(
                        AnimalesState.animales_filtrados.length() == 0,
                        # --- Estado Vacío ---
                        rx.center(
                            rx.vstack(
                                rx.icon(
                                    "search-x",
                                    size=48,
                                    color=rx.color_mode_cond(light="#cbd5e1", dark="#4b5563"),
                                ),
                                rx.text(
                                    "Sin animales activos",
                                    font_size="1.05em",
                                    weight="bold",
                                    color=_text_muted,
                                ),
                                rx.text(
                                    "Registra el primer animal usando el formulario de la izquierda.",
                                    font_size="0.82em",
                                    color=_text_muted,
                                    text_align="center",
                                    max_width="260px",
                                ),
                                spacing="2",
                                align="center",
                                padding_y="40px",
                            ),
                            width="100%",
                        ),
                        # --- Tabla Normal ---
                        rx.box(
                            rx.table.root(
                                rx.table.header(
                                    rx.table.row(
                                        rx.table.column_header_cell("ID", color=_text_muted),
                                        rx.table.column_header_cell("Código", color=_text_muted),
                                        rx.table.column_header_cell("Especie", color=_text_muted),
                                        rx.table.column_header_cell("Sexo", color=_text_muted),
                                        rx.table.column_header_cell("Categoría", color=_text_muted),
                                        rx.table.column_header_cell("Nacimiento", color=_text_muted),
                                        rx.table.column_header_cell("Dar de Baja", color=_text_muted),
                                    )
                                ),
                                rx.table.body(
                                    rx.foreach(
                                        AnimalesState.animales_filtrados,
                                        elemento_tabla_animal
                                    )
                                ),
                                width="100%",
                                variant="surface",
                            ),
                            overflow_x="auto",
                            width="100%",
                        ),
                    ),
                    width="100%",
                ),
                background_color=_card_bg,
                border=rx.color_mode_cond(light="1px solid #e2e8f0", dark="1px solid #374151"),
                flex="1",
                width="100%",
                padding="20px",
            ),
            width="100%",
            align_items="start",
            spacing="4",
            direction={"initial": "column", "lg": "row"},
        ),

        # --- Modal de Confirmación de Baja ---
        rx.alert_dialog.root(
            rx.alert_dialog.content(
                rx.alert_dialog.title(
                    rx.hstack(
                        rx.cond(
                            AnimalesState.baja_estado_pendiente == 2,
                            rx.icon("skull", color="#ef4444", size=20),
                            rx.icon("badge-dollar-sign", color="#f97316", size=20),
                        ),
                        rx.text(
                            rx.cond(
                                AnimalesState.baja_estado_pendiente == 2,
                                "Confirmar Baja por Fallecimiento",
                                "Confirmar Baja por Venta",
                            )
                        ),
                        spacing="2",
                        align="center",
                    )
                ),
                rx.alert_dialog.description(
                    rx.vstack(
                        rx.text(
                            "Estás a punto de dar de baja al animal ",
                            rx.text.strong(AnimalesState.baja_codigo_pendiente),
                            ". Esta acción lo removerá del inventario activo.",
                            font_size="0.9em",
                            color=_text_sub,
                        ),
                        rx.callout.root(
                            rx.callout.icon(rx.icon("triangle-alert", size=16)),
                            rx.callout.text(
                                "Esta operación no puede deshacerse. El animal dejará de aparecer en los módulos de Vacunación y Alimentación.",
                                font_size="0.82em",
                            ),
                            color=rx.cond(
                                AnimalesState.baja_estado_pendiente == 2,
                                "red",
                                "orange",
                            ),
                            variant="soft",
                            margin_top="10px",
                        ),
                        spacing="2",
                        align="start",
                    )
                ),
                rx.flex(
                    rx.alert_dialog.cancel(
                        rx.button(
                            rx.icon("x", size=15),
                            "Cancelar",
                            variant="soft",
                            color_scheme="gray",
                            on_click=AnimalesState.cancelar_baja,
                            cursor="pointer",
                        )
                    ),
                    rx.alert_dialog.action(
                        rx.button(
                            rx.cond(
                                AnimalesState.baja_estado_pendiente == 2,
                                rx.icon("skull", size=15),
                                rx.icon("badge-dollar-sign", size=15),
                            ),
                            rx.cond(
                                AnimalesState.baja_estado_pendiente == 2,
                                "Confirmar Fallecimiento",
                                "Confirmar Venta",
                            ),
                            color_scheme=rx.cond(
                                AnimalesState.baja_estado_pendiente == 2,
                                "red",
                                "orange",
                            ),
                            on_click=AnimalesState.confirmar_baja_animal,
                            cursor="pointer",
                        )
                    ),
                    spacing="3",
                    margin_top="16px",
                    justify="end",
                ),
                max_width="480px",
            ),
            open=AnimalesState.dialogo_baja_abierto,
        ),

        spacing="4",
        width="100%"
    )
