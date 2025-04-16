# Esta versión está adaptada para ejecución local, sin Streamlit
import matplotlib.pyplot as plt
import matplotlib.animation as animation
import numpy as np
from collections import defaultdict

# Utilidades

def extraer_coords(line):
    x_str = line.split('X')[1].split('Y')[0]
    y_str = line.split('Y')[1].split('D')[0]
    return (int(x_str)/1000, int(y_str)/1000)

def leer_gerber(filepath):
    rutas = []
    with open(filepath, 'r') as file:
        lines = file.readlines()
        inicio = None
        for line in lines:
            if 'D02' in line:
                inicio = extraer_coords(line)
            elif 'D01' in line and inicio:
                fin = extraer_coords(line)
                rutas.append((inicio, fin))
                inicio = fin
    return rutas

def leer_drl(filepath):
    puntos = []
    with open(filepath, 'r') as file:
        for line in file.readlines():
            if line.startswith('X') and 'Y' in line:
                x = int(line.split('Y')[0][1:]) / 1000
                y = int(line.split('Y')[1]) / 1000
                puntos.append((x, y))
    return puntos

# Archivos de entrada
rutas = leer_gerber("example_board.gbr")
fiduciales = leer_drl("example_board.drl")

# Agrupación por cuadrantes
cuadrantes = defaultdict(list)
for start, end in rutas:
    qx = int(min(start[0], end[0]) // 100)
    qy = int(min(start[1], end[1]) // 100)
    cuadrantes[(qx, qy)].append((start, end))

colors = ['red', 'green', 'blue', 'orange', 'purple', 'brown', 'magenta', 'cyan', 'gray']
segmentos = []
for qid, ((qx, qy), segs) in enumerate(sorted(cuadrantes.items())):
    color = colors[qid % len(colors)]
    for (start, end) in segs:
        segmentos.append((start, end, color))

# Visualización animada
fig, ax = plt.subplots(figsize=(10, 10))
ax.set_aspect('equal')
ax.set_title('Recorrido del láser por cuadrantes')
ax.set_xlabel('X (mm)')
ax.set_ylabel('Y (mm)')

max_x = max(max(p[0], q[0]) for p, q, _ in segmentos)
max_y = max(max(p[1], q[1]) for p, q, _ in segmentos)

for x in range(0, int(max_x) + 100, 100):
    ax.axvline(x, linestyle='--', color='black', linewidth=0.5)
for y in range(0, int(max_y) + 100, 100):
    ax.axhline(y, linestyle='--', color='black', linewidth=0.5)

laser_line, = ax.plot([], [], lw=2, color='red')
trace_lines = []

def init():
    laser_line.set_data([], [])
    return [laser_line]

def animate(i):
    if i >= len(segmentos):
        return trace_lines
    (x1, y1), (x2, y2), color = segmentos[i]
    line, = ax.plot([x1, x2], [y1, y2], color=color, lw=2)
    trace_lines.append(line)
    laser_line.set_data([x1, x2], [y1, y2])
    return [laser_line] + trace_lines

ani = animation.FuncAnimation(fig, animate, init_func=init,
                              frames=len(segmentos), interval=500, blit=True)

plt.show()

# Generar G-code
with open("ruta_laser.gcode", "w") as f:
    f.write("G21 ; usar mm\n")
    f.write("G90 ; posicionamiento absoluto\n")
    f.write("M3  ; encender láser\n")
    for (qx, qy), segmentos_cuadrante in sorted(cuadrantes.items()):
        f.write(f"\n; ---- Comienzo cuadrante ({qx}, {qy}) ----\n")
        f.write(f"; Mover origen a X={qx*100} Y={qy*100}\n")
        for (x1, y1), (x2, y2) in segmentos_cuadrante:
            local_x1, local_y1 = x1 - qx * 100, y1 - qy * 100
            local_x2, local_y2 = x2 - qx * 100, y2 - qy * 100
            f.write(f"G0 X{local_x1:.2f} Y{local_y1:.2f}\n")
            f.write(f"G1 X{local_x2:.2f} Y{local_y2:.2f} F100\n")
        f.write(f"; ---- Fin cuadrante ({qx}, {qy}) ----\n")
    f.write("M5 ; apagar láser\n")
    f.write("G0 X0 Y0 ; volver al origen\n")
print("G-code generado y guardado en ruta_laser.gcode")
