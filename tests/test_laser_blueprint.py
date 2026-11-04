import math
import xml.etree.ElementTree as ET

def check_svg(svg_path):
    print(f"=== Checking {svg_path} ===")
    tree = ET.parse(svg_path)
    root = tree.getroot()

    elements = []
    for elem in root.iter():
        stroke = elem.get('stroke', '')
        if stroke != '#FF0000':
            continue
        tag = elem.tag.split('}')[-1]
        if tag == 'circle':
            cx = float(elem.get('cx'))
            cy = float(elem.get('cy'))
            r = float(elem.get('r'))
            elements.append(('circle', cx, cy, r))
        elif tag == 'rect':
            x = float(elem.get('x'))
            y = float(elem.get('y'))
            w = float(elem.get('width'))
            h = float(elem.get('height'))
            elements.append(('rect', x, y, w, h))

    circles = [e for e in elements if e[0] == 'circle']
    rects = [e for e in elements if e[0] == 'rect']

    print(f"Total cut circles: {len(circles)}, cut rects: {len(rects)}")

    issues = 0
    for i in range(len(circles)):
        _, c1x, c1y, r1 = circles[i]
        for j in range(i + 1, len(circles)):
            _, c2x, c2y, r2 = circles[j]
            dist = math.hypot(c1x - c2x, c1y - c2y)
            if dist < r1 + r2:
                print(f"[OVERLAP] Circles ({c1x:.2f}, {c1y:.2f}, r={r1}) and ({c2x:.2f}, {c2y:.2f}, r={r2}) - dist={dist:.2f} < sum_r={r1+r2:.2f}")
                issues += 1
            elif dist < r1 + r2 + 1.2:
                print(f"[THIN WALL <1.2mm] Circles ({c1x:.2f}, {c1y:.2f}, r={r1}) and ({c2x:.2f}, {c2y:.2f}, r={r2}) - wall={dist - (r1+r2):.2f}mm")
                issues += 1

    for c in circles:
        _, cx, cy, r = c
        for rect in rects:
            _, rx, ry, rw, rh = rect
            if rw >= 24 and rh >= 15:
                if rx <= cx <= rx + rw and ry <= cy <= ry + rh:
                    dx = min(cx - rx, rx + rw - cx)
                    dy = min(cy - ry, ry + rh - cy)
                    min_edge = min(dx, dy)
                    if min_edge < r:
                        print(f"[CUTS EDGE] Circle ({cx:.2f}, {cy:.2f}) cuts plate edge")
                        issues += 1
                    elif min_edge - r < 1.0:
                        print(f"[EDGE MARGIN <1mm] Circle ({cx:.2f}, {cy:.2f}, r={r}) margin={min_edge - r:.2f}mm")
                        issues += 1
            else:
                closest_x = max(rx, min(cx, rx + rw))
                closest_y = max(ry, min(cy, ry + rh))
                dist = math.hypot(cx - closest_x, cy - closest_y)
                if dist < r:
                    print(f"[OVERLAP] Circle ({cx:.2f}, {cy:.2f}, r={r}) intersects slot [{rx:.2f}, {ry:.2f}, {rw:.2f}, {rh:.2f}]")
                    issues += 1
                elif dist - r < 1.0:
                    print(f"[THIN WALL <1mm] Circle ({cx:.2f}, {cy:.2f}, r={r}) slot margin={dist - r:.2f}mm")
                    issues += 1

    if issues == 0:
        print(">>> PERFECT! ZERO OVERLAPS, ZERO THIN WALLS, ZERO CRITICAL EDGE MARGINS! <<<")
    else:
        print(f"Total issues found: {issues}")

if __name__ == "__main__":
    check_svg("hardware/laser_cut/walle_chassis_complete_cutsheet.svg")
    check_svg("hardware/laser_cut/walle_charging_dock_cutsheet.svg")
