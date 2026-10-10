import math

def calculate_bounds(size, is_tray):
    center_x = size / 2
    center_y = size / 2
    radius = size * 0.48 if is_tray else size * 0.38
    
    max_hx_edge = 0
    max_hy_edge = 0
    max_px = 0
    
    points_nd = []
    if is_tray:
        for i in range(8):
            x = -0.5 if (i & 1) == 0 else 0.5
            y = -0.5 if (i & 2) == 0 else 0.5
            z = -0.5 if (i & 4) == 0 else 0.5
            points_nd.append([x, y, z])
    else:
        for i in range(32):
            x = -0.5 if (i & 1) == 0 else 0.5
            y = -0.5 if (i & 2) == 0 else 0.5
            z = -0.5 if (i & 4) == 0 else 0.5
            w = -0.5 if (i & 8) == 0 else 0.5
            v = -0.5 if (i & 16) == 0 else 0.5
            points_nd.append([x, y, z, w, v])

    for r in range(1000):
        rotation = r / 100.0
        
        orbit_radius = radius * (0.70 if is_tray else 0.52)
        happy_z = math.cos(rotation * 2.7)
        happy_x = center_x + orbit_radius * math.sin(rotation * 2.7)
        happy_y = center_y + orbit_radius * math.sin(rotation * 1.4) * math.cos(rotation * 0.9)
        
        base_size = radius * (0.35 if is_tray else 0.22)
        depth_scale = 1.0 + (happy_z * 0.35)
        green_icon_w = int(base_size * depth_scale)
        green_icon_h = green_icon_w
        
        hx_edge = happy_x + green_icon_w / 2
        hy_edge = happy_y + green_icon_h / 2
        max_hx_edge = max(max_hx_edge, hx_edge)
        max_hy_edge = max(max_hy_edge, hy_edge)
        
        if is_tray:
            rot_xy = rotation * 1.2
            rot_yz = rotation * 0.7
            rot_xz = rotation * 0.9
            c_xy, s_xy = math.cos(rot_xy), math.sin(rot_xy)
            c_yz, s_yz = math.cos(rot_yz), math.sin(rot_yz)
            c_xz, s_xz = math.cos(rot_xz), math.sin(rot_xz)
            
            for p in points_nd:
                x, y, z = p[0], p[1], p[2]
                x1 = x * c_xy - y * s_xy
                y1 = x * s_xy + y * c_xy
                x, y = x1, y1
                y1 = y * c_yz - z * s_yz
                z1 = y * s_yz + z * c_yz
                y, z = y1, z1
                x1 = x * c_xz - z * s_xz
                z1 = x * s_xz + z * c_xz
                x, z = x1, z1
                z_factor = 1.0 / (2.0 - z)
                x2 = x * z_factor
                scale = radius * 1.8
                px = center_x + x2 * scale
                max_px = max(max_px, px)
        else:
            rot_xy = rotation * 1.2
            rot_zw = rotation * 0.7
            rot_xw = rotation * 0.9
            rot_yv = rotation * 0.5
            rot_zv = rotation * 1.1
            c_xy, s_xy = math.cos(rot_xy), math.sin(rot_xy)
            c_zw, s_zw = math.cos(rot_zw), math.sin(rot_zw)
            c_xw, s_xw = math.cos(rot_xw), math.sin(rot_xw)
            c_yv, s_yv = math.cos(rot_yv), math.sin(rot_yv)
            c_zv, s_zv = math.cos(rot_zv), math.sin(rot_zv)
            
            for p in points_nd:
                x, y, z, w, v = p[0], p[1], p[2], p[3], p[4]
                y1 = y * c_yv - v * s_yv
                v1 = y * s_yv + v * c_yv
                y, v = y1, v1
                z1 = z * c_zv - v * s_zv
                v1 = z * s_zv + v * c_zv
                z, v = z1, v1
                x1 = x * c_xy - y * s_xy
                y1 = x * s_xy + y * c_xy
                x, y = x1, y1
                z1 = z * c_zw - w * s_zw
                w1 = z * s_zw + w * c_zw
                z, w = z1, w1
                x1 = x * c_xw - w * s_xw
                w1 = x * s_xw + w * c_xw
                x, w = x1, w1
                
                v_factor = 1.0 / (2.0 - v)
                x = x * v_factor
                y = y * v_factor
                z = z * v_factor
                w = w * v_factor
                w_factor = 1.0 / (2.0 - w)
                x = x * w_factor
                y = y * w_factor
                z = z * w_factor
                
                z += math.sin(rotation * 2.0) * 0.1
                z_factor = 1.0 / (2.0 - z)
                x2 = x * z_factor
                scale = radius * 3.4
                px = center_x + x2 * scale
                max_px = max(max_px, px)

    print(f"Size: {size}, Is Tray: {is_tray}")
    print(f"  Max green file edge X: {max_hx_edge}")
    print(f"  Max Penteract Vertex X: {max_px}")

calculate_bounds(260, False)
calculate_bounds(256, True)
