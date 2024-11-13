import os


def merge_gcode(p1, p2, p3, output_file):
    """
    Merge multiple G-code files and add tilt commands.

    Parameters:
    p1 (str): Path to the first G-code file
    p2 (str): Path to the second G-code file
    p3 (str): Path to the third G-code file
    output_file (str): Path to the output merged G-code file
    """
    max_heights = [0, 0, 0]

    with open(output_file, 'w') as outfile:
        # Process first part
        with open(p1, 'r') as infile:
            outfile.write(f'G87 X0 Y0 Z0 A0 B0 C0\n')
            for line in infile:
                parts = line.split()
                if len(parts) >= 4 and (parts[0] == 'G1' or parts[0] == 'G0'):
                    z_value = float(parts[2][1:])
                    max_heights[0] = max(max_heights[0], z_value)
                outfile.write(line)

        # Process second part
        with open(p2, 'r') as infile:
            outfile.write(f'G87 X0 Y0 Z{max_heights[0]} A0 B30 C0\n')
            for line in infile:
                parts = line.split()
                if len(parts) >= 4 and (parts[0] == 'G1' or parts[0] == 'G0'):
                    z_value = float(parts[2][1:])
                    max_heights[1] = max(max_heights[1], z_value)
                outfile.write(line)

        # Process third part
        with open(p3, 'r') as infile:
            outfile.write(f'G87 X0 Y0 Z{max_heights[1]} A0 B-15 C0\n')
            for line in infile:
                parts = line.split()
                if len(parts) >= 4 and (parts[0] == 'G1' or parts[0] == 'G0'):
                    z_value = float(parts[2][1:])
                    max_heights[2] = max(max_heights[2], z_value)
                outfile.write(line)


# Example usage
merge_gcode('p1_t.gcode', 'p2_t.gcode', 'p3_t.gcode', 'merged_output_t.gcode')