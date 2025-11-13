"""
Generador de Pedidos con historial de estados
"""
import random
from datetime import datetime, timedelta
from ..config import Config
from ..sample_data import SampleData
from ..helpers import Helpers


class PedidosGenerator:
    """Generador de datos para la tabla Pedidos con historial de estados"""
    
    ESTADOS = ["procesando", "cocinando", "empacando", "enviando", "recibido"]
    
    # Mapeo de estados a roles de empleados
    # Nota: "procesando" y "recibido" NO tienen empleado asignado
    ESTADO_A_ROL = {
        "cocinando": "cocinero",
        "empacando": "despachador",
        "enviando": "repartidor"
    }
    
    @classmethod
    def generar_pedidos(cls, locales_ids, usuarios, productos, productos_por_local, empleados_por_local, combos_por_local):
        """Genera pedidos con historial de estados"""
        pedidos = []
        
        # Filtrar solo usuarios con rol "Cliente" que tengan información bancaria
        usuarios_validos = [u for u in usuarios if u.get("informacion_bancaria") and u.get("role") == "Cliente"]
        
        if not usuarios_validos:
            print("  ⚠️  No hay usuarios Cliente con información bancaria")
            return pedidos, []
        
        print(f"  ℹ️  Usuarios Cliente válidos para pedidos: {len(usuarios_validos)}")
        
        # Crear diccionario de productos por nombre para búsqueda rápida
        productos_dict = {p["nombre"]: p for p in productos}
        
        for i in range(Config.NUM_PEDIDOS):
            local_id = random.choice(locales_ids)
            usuario = random.choice(usuarios_validos)
            
            pedido = cls._crear_pedido_con_historial(
                local_id, usuario, productos_dict, productos_por_local, empleados_por_local, combos_por_local
            )
            
            pedidos.append(pedido)
            
            if (i + 1) % 1000 == 0:
                print(f"  📊 Progreso: {i + 1}/{Config.NUM_PEDIDOS}")
        
        pedidos_ids = [p["pedido_id"] for p in pedidos]
        print(f"  ✅ {len(pedidos)} pedidos generados")
        print(f"  ℹ️  Empleados asignados solo en estados: cocinando, empacando, enviando")
        
        return pedidos, pedidos_ids
    
    @classmethod
    def _crear_pedido_con_historial(cls, local_id, usuario, productos_dict, productos_por_local, empleados_por_local, combos_por_local):
        """Crea un pedido con historial de estados"""
        pedido_id = Helpers.generar_uuid()
        
        # Decidir si el pedido incluye productos, combos o ambos
        tipo_pedido = random.choices(
            ["solo_productos", "solo_combos", "mixto"],
            weights=[50, 30, 20],
            k=1
        )[0]
        
        costo_total = 0
        productos_pedido = []
        combos_pedido = []
        
        # Generar productos si corresponde
        if tipo_pedido in ["solo_productos", "mixto"]:
            productos_disponibles = productos_por_local.get(local_id, [])
            
            if productos_disponibles:
                num_productos = min(random.randint(1, 4), len(productos_disponibles))
                productos_seleccionados = random.sample(productos_disponibles, num_productos)
                
                for nombre_producto in productos_seleccionados:
                    if nombre_producto in productos_dict:
                        cantidad = random.randint(1, 3)
                        precio_unitario = productos_dict[nombre_producto]["precio"]
                        
                        productos_pedido.append({
                            "nombre": nombre_producto,
                            "cantidad": cantidad
                        })
                        
                        costo_total += precio_unitario * cantidad
        
        # Generar combos si corresponde
        if tipo_pedido in ["solo_combos", "mixto"]:
            combos_disponibles = combos_por_local.get(local_id, [])
            
            if combos_disponibles:
                num_combos = min(random.randint(1, 2), len(combos_disponibles))
                combos_seleccionados = random.sample(combos_disponibles, num_combos)
                
                for combo_id in combos_seleccionados:
                    cantidad = random.randint(1, 2)
                    # Estimar precio del combo (aproximadamente 15-35 soles)
                    precio_combo = random.uniform(15.0, 35.0)
                    
                    combos_pedido.append({
                        "combo_id": combo_id,
                        "cantidad": cantidad
                    })
                    
                    costo_total += precio_combo * cantidad
        
        # Si no hay productos ni combos, forzar al menos un producto
        if not productos_pedido and not combos_pedido:
            productos_disponibles = productos_por_local.get(local_id, [])
            if productos_disponibles:
                nombre_producto = random.choice(productos_disponibles)
                if nombre_producto in productos_dict:
                    productos_pedido.append({
                        "nombre": nombre_producto,
                        "cantidad": 1
                    })
                    costo_total += productos_dict[nombre_producto]["precio"]
        
        # Agregar costo de delivery
        costo_total += random.uniform(3.0, 8.0)
        
        # Determinar estado actual del pedido
        estado_actual = random.choices(
            cls.ESTADOS,
            weights=[10, 20, 15, 25, 30],
            k=1
        )[0]
        
        fecha_base = datetime.now() - timedelta(hours=random.randint(0, 72))
        
        # Calcular fecha de entrega aproximada
        total_items = len(productos_pedido) + len(combos_pedido)
        fecha_entrega_aproximada = cls._calcular_fecha_entrega(fecha_base, total_items)
        
        # Generar historial de estados
        historial_estados = cls._generar_historial_estados(
            estado_actual, fecha_base, local_id, empleados_por_local
        )
        
        # IMPORTANTE: Direccion SIEMPRE presente (requerida por schema)
        # Usar direccion_delivery del usuario o una aleatoria
        direccion_pedido = usuario.get("informacion_bancaria", {}).get("direccion_delivery")
        if not direccion_pedido:
            direccion_pedido = random.choice(SampleData.DIRECCIONES_LIMA)
        
        pedido = {
            "local_id": local_id,
            "pedido_id": pedido_id,
            "usuario_correo": usuario["correo"],
            "costo": round(costo_total, 2),
            "fecha_entrega_aproximada": fecha_entrega_aproximada,
            "direccion": direccion_pedido,
            "estado": estado_actual,
            "historial_estados": historial_estados
        }
        
        # Agregar productos solo si existen
        if productos_pedido:
            pedido["productos"] = productos_pedido
        
        # Agregar combos solo si existen
        if combos_pedido:
            pedido["combos"] = combos_pedido
        
        return pedido
    
    @classmethod
    def _calcular_fecha_entrega(cls, fecha_base, num_productos):
        """Calcula fecha de entrega aproximada basada en número de productos"""
        tiempo_preparacion = 30 + max(0, (num_productos - 1) * 5)
        tiempo_delivery = random.randint(20, 30)
        tiempo_total = tiempo_preparacion + tiempo_delivery
        
        fecha_entrega = fecha_base + timedelta(minutes=tiempo_total)
        return fecha_entrega.isoformat()
    
    @classmethod
    def _generar_historial_estados(cls, estado_actual, fecha_base, local_id, empleados_por_local):
        """
        Genera el historial de estados como un array.
        Solo incluye estados hasta el estado actual.
        """
        historial = []
        tiempo_acumulado = 0
        estado_actual_index = cls.ESTADOS.index(estado_actual)
        
        # Obtener empleados DEL LOCAL específico
        empleados_del_local = empleados_por_local.get(local_id, {
            "cocinero": [],
            "despachador": [],
            "repartidor": [],
            "info_empleados": {}
        })
        
        for idx, estado in enumerate(cls.ESTADOS):
            if idx <= estado_actual_index:
                es_estado_actual = (idx == estado_actual_index)
                
                hora_inicio = fecha_base + timedelta(minutes=tiempo_acumulado)
                duracion = cls._obtener_duracion_estado(estado)
                hora_fin = hora_inicio + timedelta(minutes=duracion)
                
                # Crear entrada en el historial
                entrada_historial = {
                    "estado": estado,
                    "hora_inicio": hora_inicio.isoformat(),
                    "hora_fin": hora_fin.isoformat(),
                    "activo": es_estado_actual
                }
                
                # Agregar información del empleado si el estado lo requiere
                if estado in cls.ESTADO_A_ROL:
                    rol = cls.ESTADO_A_ROL[estado]
                    empleado_info = cls._obtener_info_empleado(
                        empleados_del_local, rol
                    )
                    
                    if empleado_info:
                        entrada_historial["empleado"] = empleado_info
                    else:
                        entrada_historial["empleado"] = None
                else:
                    entrada_historial["empleado"] = None
                
                historial.append(entrada_historial)
                tiempo_acumulado += duracion
        
        return historial
    
    @classmethod
    def _obtener_info_empleado(cls, empleados_del_local, rol):
        """Obtiene información de un empleado del local para un rol específico"""
        empleados_del_rol = empleados_del_local.get(rol, [])
        
        if not empleados_del_rol:
            return None
        
        empleado_dni = random.choice(empleados_del_rol)
        empleado_data = empleados_del_local["info_empleados"].get(empleado_dni, {})
        
        return {
            "dni": empleado_dni,
            "nombre_completo": f"{empleado_data.get('nombre', '')} {empleado_data.get('apellido', '')}".strip(),
            "rol": rol,
            "calificacion_prom": empleado_data.get("calificacion_prom", round(random.uniform(3.5, 5.0), 2))
        }
    
    @classmethod
    def _obtener_duracion_estado(cls, estado):
        """Retorna la duración típica de cada estado en minutos"""
        duraciones = {
            "procesando": random.randint(2, 5),
            "cocinando": random.randint(15, 30),
            "empacando": random.randint(3, 8),
            "enviando": random.randint(20, 45),
            "recibido": 0
        }
        return duraciones.get(estado, 5)
