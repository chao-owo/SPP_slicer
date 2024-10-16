import re
import math


class GCodePostProcessor:
    def __init__(self, pipe_radius, bend_angle):
        self.pipe_radius = pipe_radius
        self.total_bend_angle = math.radians(bend_angle)
        self.current_layer = 0
        self.layer_height = 0
        self.total_height = 0
        self.layers = []

    def process_file(self, input_file, output_file):
        # First pass: analyze the G-code to determine layers and total height
        self.analyze_gcode(input_file)

        # Calculate total height and layer angles
        self.total_height = len(self.layers) * self.layer_height
        self.calculate_layer_angles()

        # Second pass: process the G-code with calculated angles
        with open(input_file, 'r') as infile, open(output_file, 'w') as outfile:
            self.current_layer = 0
            for line in infile:
                processed_line = self.process_line(line)
                outfile.write(processed_line + '\n')

    def analyze_gcode(self, input_file):
        with open(input_file, 'r') as infile:
            current_z = 0
            for line in infile:
                if line.startswith(';LAYER:'):
                    self.layers.append(current_z)
                elif line.startswith('G1 ') and 'Z' in line:
                    z_match = re.search(r'Z([-\d.]+)', line)
                    if z_match:
                        new_z = float(z_match.group(1))
                        if new_z > current_z:
                            current_z = new_z
                            if len(self.layers) == 1:
                                self.layer_height = current_z - self.layers[0]

    def calculate_layer_angles(self):
        for i, layer_z in enumerate(self.layers):
            progress = layer_z / self.total_height
            angle = progress * self.total_bend_angle
            self.layers[i] = (layer_z, angle)

    def process_line(self, line):
        if line.startswith(';LAYER:'):
            self.current_layer = int(line.split(':')[1])
            return line.strip()
        elif line.startswith('G1 '):
            return self.adjust_coordinates_and_flow(line)
        return line.strip()

    def adjust_coordinates_and_flow(self, line):
        match = re.search(r'X([-\d.]+)\s*Y([-\d.]+)\s*Z([-\d.]+)(\s*E([-\d.]+))?', line)
        if match:
            x, y, z = map(float, match.group(1, 2, 3))
            e = float(match.group(5)) if match.group(5) else None

            # Get the current layer's angle
            layer_z, layer_angle = self.layers[self.current_layer]

            # Calculate new coordinates based on pipe bending
            new_x = x * math.cos(layer_angle) - z * math.sin(layer_angle)
            new_z = x * math.sin(layer_angle) + z * math.cos(layer_angle)

            # Adjust flow (E) based on the new position
            if e is not None:
                # Calculate the arc length ratio for flow adjustment
                outer_radius = self.pipe_radius + x
                inner_radius = self.pipe_radius - x
                arc_length_ratio = outer_radius / inner_radius
                new_e = e * arc_length_ratio

                return f"G1 X{new_x:.3f} Y{y:.3f} Z{new_z:.3f} E{new_e:.5f}"
            else:
                return f"G1 X{new_x:.3f} Y{y:.3f} Z{new_z:.3f}"
        return line.strip()


def main():
    pipe_radius = 50  # Radius of the pipe in mm
    bend_angle = 90  # Total bend angle of the pipe in degrees
    input_file = 'input.gcode'
    output_file = 'output.gcode'

    processor = GCodePostProcessor(pipe_radius, bend_angle)
    processor.process_file(input_file, output_file)
    print(f"Processed G-code saved to {output_file}")


if __name__ == "__main__":
    main()