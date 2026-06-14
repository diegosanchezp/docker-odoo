# Inventario: Reglas de Reabastecimiento por Prioridad

1. Cree o edite un producto Inventario -> Productos -> Productos.

2. En la pestaña de Información general Asigne un "Stock objetivo" y "Prioridad de Reabastecimiento".
![Campos de Stock objetivo y Prioridad de reabastecimiento - Vista formulario de producto](./img/inventario_reglas_reabastecimiento_prioridad/campos_stock_objetivo_prioridad_reabastecimiento_producto.png) 

3. Espere 5 minutos a que se ejecute el cronjob de "Verificar existencia de Productos a reabastecer". O ejecútelo manualmente.
![Cronjob de Verificar existencia de Productos a reabastecer](./img/inventario_reglas_reabastecimiento_prioridad/cronjob_existencia_productos.png) 

4. Visite la vista lista de "Pendientes de reabastecimiento" ->
![Menu de vista lista de Pendientes de reabastecimiento](./img/inventario_reglas_reabastecimiento_prioridad/punto_menu_pendientes_reabastecimiento.png) 

5. Verifique que se ha creado una nueva entrada
![Vista lista de Pendientes de reabastecimiento](./img/inventario_reglas_reabastecimiento_prioridad/vista_lista_pendientes_reabastecimiento.png) 

6. Verifique que se ha creado una nueva actividad planificada para el responsable del almacén.

![Actividad asignada en la vista formulario de producto](./img/inventario_reglas_reabastecimiento_prioridad/asignacion_actividad.png)

## Notas técnicas
El responsable del almacén es el usuario encargado del almacén en donde esta guardado el producto. Si no se encuentra, el administrador será el responsable.
![Responsable de alamacen](./img/inventario_reglas_reabastecimiento_prioridad/responsable_almacen_campo_direccion.png) 

# Inventario: Clasificación Operativa de Productos

1. Cree etiquetas en Inventario -> Configuración -> Etiquetas Producto.
![Menu - Vista etiquetas de producto](./img/inventario_clasificacion_operativa_de_productos/etiquetas_producto.png) 

![Formulario de Etiquetas](./img/inventario_clasificacion_operativa_de_productos/etiquetas_form_muebleria.png)
2. Asigne las a productos. Inventario -> Productos -> Productos.
![Asignación etiqueta a producto](./img/inventario_clasificacion_operativa_de_productos/asignacion-etiqueta-a-producto.png)

. Diríjase a la vista de "Operativa de productos" en Inventario -> Productos -> Operativa de productos.
![Menú vista operativa producto](./img/inventario_clasificacion_operativa_de_productos/menu_vista_operativa_producto.png)
. Puede agrupar por tipo de operación o etiquetas. Por defecto se agrupa por tipo de operación.
![Vista de "Operativa de productos"](./img/inventario_clasificacion_operativa_de_productos/filtros-de-agrupacion.png) 

