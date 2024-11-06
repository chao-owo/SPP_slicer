import re
import math
import numpy as np


class GCodePipeConnector:
    def __init__(self, tilt_angle_degrees=45):
        self.tilt_angle = math.radians(tilt_angle_degrees)
        self.first_part_max_z = 0
        self.pivot_x = 0
        self.pivot_y = 0
        self.rotation_matrix = None
        self.min_z_second_part = float('inf')
        self.bounding_box = {'min_x': float('inf'), 'max_x': float('-inf'),
                             'min_y': float('inf'), 'max_y': float('-inf')}
        self.pipe_diameter = None
        self.wall_thickness = None

    def analyze_first_part(self, filename):
        """Find the maximum Z height, pipe diameter, and wall thickness from first part"""
        max_z = 0
        x_coords = []
        y_coords = []
        current_z = 0

        with open(filename, 'r') as file:
            for line in file:
                if line.startswith('G0 ') or line.startswith('G1 '):
                    z_match = re.search(r'Z([-\d.]+)', line)
                    x_match = re.search(r'X([-\d.]+)', line)
                    y_match = re.search(r'Y([-\d.]+)', line)

                    if z_match:
                        current_z = float(z_match.group(1))
                        max_z = max(max_z, current_z)

                    if x_match and y_match:
                        x = float(x_match.group(1))
                        y = float(y_match.group(1))
                        x_coords.append(x)
                        y_coords.append(y)

        # Calculate pipe properties from coordinates
        if x_coords and y_coords:
            x_range = max(x_coords) - min(x_coords)
            y_range = max(y_coords) - min(y_coords)
            self.pipe_diameter = max(x_range, y_range)
            # Assume wall thickness is 10% of diameter if not directly measurable
            self.wall_thickness = self.pipe_diameter * 0.1

        self.first_part_max_z = max_z
        self.pivot_x = (min(x_coords) + max(x_coords)) / 2
        self.pivot_y = (min(y_coords) + max(y_coords)) / 2

    def get_transformation_matrices(self):
        """Create transformation matrices for angled pipe connection"""
        cos_t = math.cos(self.tilt_angle)
        sin_t = math.sin(self.tilt_angle)

        # Create rotation matrix around Y axis
        self.rotation_matrix = np.array([
            [cos_t, 0, sin_t],
            [0, 1, 0],
            [-sin_t, 0, cos_t]
        ])

    def transform_point(self, x, y, z):
        """Transform a point using the rotation matrix with offset for pipe connection"""
        # Calculate offset based on pipe diameter for proper connection
        connection_offset = self.pipe_diameter * 0.5

        # Adjust Z coordinate to account for connection height
        adjusted_z = z - self.min_z_second_part

        # Create point vector relative to pivot
        point = np.array([
            x - self.pivot_x,
            y - self.pivot_y,
            adjusted_z + connection_offset
        ])

        # Apply rotation
        rotated = np.dot(self.rotation_matrix, point)

        # Add offset for clean connection
        transformed = [
            rotated[0] + self.pivot_x,
            rotated[1] + self.pivot_y,
            rotated[2] + self.first_part_max_z - connection_offset * math.cos(self.tilt_angle)
        ]

        return transformed

    def process_files(self, first_part_file, second_part_file, output_file):
        # Analyze parts and set up transformation
        self.analyze_first_part(first_part_file)
        self.analyze_second_part(second_part_file)
        self.get_transformation_matrices()

        with open(output_file, 'w') as outfile:
            # Copy first part
            with open(first_part_file, 'r') as first_part:
                for line in first_part:
                    outfile.write(line)

            # Add transition commands with proper retraction
            outfile.write('\n; Starting angled pipe connection\n')
            outfile.write('G92 E0 ; Reset extruder\n')
            outfile.write('G1 F2400 E-3 ; Retract filament\n')
            outfile.write(f'G0 F5000 Z{self.first_part_max_z + 5} ; Lift Z\n\n')

            # Process second part with transformations
            with open(second_part_file, 'r') as second_part:
                for line in second_part:
                    processed_line = self.process_line(line)
                    if processed_line:
                        outfile.write(processed_line + '\n')

    def process_line(self, line):
        """Process a single line of G-code"""
        if line.startswith('G0 ') or line.startswith('G1 '):
            return self.transform_movement(line)
        elif line.startswith(';'):
            return line.strip()
        else:
            return line.strip()

    def analyze_second_part(self, filename):
        """Analyze second part for minimum Z height"""
        with open(filename, 'r') as file:
            for line in file:
                if line.startswith('G0 ') or line.startswith('G1 '):
                    z_match = re.search(r'Z([-\d.]+)', line)
                    if z_match:
                        z = float(z_match.group(1))
                        self.min_z_second_part = min(self.min_z_second_part, z)

    def transform_movement(self, line):
        """Transform a movement command for angled pipe connection"""
        coords = {'X': None, 'Y': None, 'Z': None, 'E': None, 'F': None}

        for param in coords.keys():
            match = re.search(f'{param}([-\d.]+)', line)
            if match:
                coords[param] = float(match.group(1))

        if all(v is None for v in [coords['X'], coords['Y'], coords['Z']]):
            return line.strip()

        x = coords['X'] if coords['X'] is not None else self.pivot_x
        y = coords['Y'] if coords['Y'] is not None else self.pivot_y
        z = coords['Z'] if coords['Z'] is not None else self.min_z_second_part

        new_point = self.transform_point(x, y, z)

        command = line[:2]
        parts = []

        if coords['X'] is not None:
            parts.append(f'X{new_point[0]:.3f}')
        if coords['Y'] is not None:
            parts.append(f'Y{new_point[1]:.3f}')
        if coords['Z'] is not None:
            parts.append(f'Z{new_point[2]:.3f}')
        if coords['E'] is not None:
            parts.append(f'E{coords["E"]:.5f}')
        if coords['F'] is not None:
            parts.append(f'F{coords["F"]}')

        return command + ' ' + ' '.join(parts)



def main():
    first_part_file = 'part1.gcode'
    second_part_file = 'part2.gcode'
    output_file = 'combined_tilted_output.gcode'

    processor = GCodePipeConnector(tilt_angle_degrees=45)
    processor.process_files(first_part_file, second_part_file, output_file)
    print(f"Combined G-code with tilted base saved to {output_file}")


if __name__ == "__main__":
    main()