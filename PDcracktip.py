# Copyright (c) 2024 Yangyuanchen Liu. All rights reserved.
# https://orcid.org/0000-0002-7730-8287 (ORCID)
# liuyangyuanchen@outlook.com (email)
# License: http://opensource.org/licenses/MIT

from paraview.util.vtkAlgorithm import *
from paraview import vtk

@smproxy.filter(name="PDcracktip", label="Phase Field Crack Tip")
@smproperty.input(name="Input")
@smdomain.datatype(dataTypes=["vtkUnstructuredGrid"], composite_data_supported=True)
class PDcracktip(VTKPythonAlgorithmBase):
    """
    Filter to find the crack tip location based on phase field values.
    """
    def __init__(self):
        super().__init__(nInputPorts=1, nOutputPorts=1, outputType="vtkUnstructuredGrid")
        self._d_c = 0.5
        self._array_name = 'd'
        self._initial_tip = [0.0, 0.0, 0.0]
        self._global_current_tip = self._initial_tip
        self._global_max_distance_sq = -1
        self._region_min = [-vtk.VTK_FLOAT_MAX, -vtk.VTK_FLOAT_MAX, -vtk.VTK_FLOAT_MAX]
        self._region_max = [vtk.VTK_FLOAT_MAX, vtk.VTK_FLOAT_MAX, vtk.VTK_FLOAT_MAX]

    @smproperty.doublevector(name="CriticalPhaseFieldValue", default_values=0.5)
    @smdomain.xml("""
        <DoubleRangeDomain name="range" min="0.0" max="1.0"/>
    """)
    def SetCriticalPhaseFieldValue(self, value):
        self._d_c = value
        self.Modified()
        print(f"SetCriticalPhaseFieldValue called with value: {value}")

    @smproperty.doublevector(name="InitialTipLocation", default_values=[0.0, 0.0, 0.0], number_of_elements=3)
    def SetInitialTipLocation(self, x, y, z):
        self._initial_tip = [x, y, z]
        self.Modified()
        print(f"SetInitialTipLocation called with value: {self._initial_tip}")

    @smproperty.doublevector(name="RegionMin", default_values=[-vtk.VTK_FLOAT_MAX, -vtk.VTK_FLOAT_MAX, -vtk.VTK_FLOAT_MAX], number_of_elements=3)
    def SetRegionMin(self, x, y, z):
        self._region_min = [x, y, z]
        self.Modified()
        print(f"SetRegionMin called with value: {self._region_min}")

    @smproperty.doublevector(name="RegionMax", default_values=[vtk.VTK_FLOAT_MAX, vtk.VTK_FLOAT_MAX, vtk.VTK_FLOAT_MAX], number_of_elements=3)
    def SetRegionMax(self, x, y, z):
        self._region_max = [x, y, z]
        self.Modified()
        print(f"SetRegionMax called with value: {self._region_max}")

    @smproperty.stringvector(name="ArrayList", information_only="1")
    def GetArrayList(self):
        input_data = self.GetInputDataObject(0, 0)
        array_names = set()

        if input_data:
            point_data = input_data.GetPointData()
            for i in range(point_data.GetNumberOfArrays()):
                array_names.add(point_data.GetArrayName(i))

        return list(array_names)

    @smproperty.stringvector(name="ArrayName", number_of_elements=1)
    @smdomain.xml("""
        <StringListDomain name="array_list">
            <RequiredProperties>
                <Property name="ArrayList" function="ArrayList"/>
            </RequiredProperties>
        </StringListDomain>
    """)
    def SetArrayName(self, array_name):
        if array_name and array_name != 'None':
            self._array_name = array_name
            self.Modified()
            print(f"SetArrayName called with array name: {array_name}")
        else:
            print("Error: SetArrayName called with None or invalid array name")

    def ProcessBlock(self, block):
        if isinstance(block, vtk.vtkUnstructuredGrid):
            print(f"Processing block of type: {block.GetClassName()}")

            point_data = block.GetPointData()
            print(f"Point data has {point_data.GetNumberOfArrays()} arrays")

            phase_field_array = point_data.GetArray(self._array_name)
            if not phase_field_array:
                print(f"Error: '{self._array_name}' array not found in block of type {block.GetClassName()}.")
                return

            print(f"Found array: {self._array_name} in block of type: {block.GetClassName()}")

            # Filter points where d > d_c and within the specified region
            for i in range(block.GetNumberOfPoints()):
                point = block.GetPoint(i)
                if (self._region_min[0] <= point[0] <= self._region_max[0] and
                    self._region_min[1] <= point[1] <= self._region_max[1] and
                    self._region_min[2] <= point[2] <= self._region_max[2] and
                    phase_field_array.GetValue(i) > self._d_c):
                    distance_sq = (
                        (point[0] - self._initial_tip[0])**2 +
                        (point[1] - self._initial_tip[1])**2 +
                        (point[2] - self._initial_tip[2])**2
                    )
                    if distance_sq > self._global_max_distance_sq:
                        self._global_max_distance_sq = distance_sq
                        self._global_current_tip = point

    def RequestData(self, request, inInfo, outInfo):
        print(f"RequestData called with d_c: {self._d_c} and array name: {self._array_name}")

        input_data = self.GetInputData(inInfo, 0, 0)
        output_data = self.GetOutputData(outInfo, 0)

        self._global_max_distance_sq = -1
        self._global_current_tip = self._initial_tip

        if isinstance(input_data, vtk.vtkUnstructuredGrid):
            self.ProcessBlock(input_data)
        else:
            print("Unsupported input data type")
            return 0

        # Output only one point, the global_current_tip
        filtered_points = vtk.vtkPoints()
        filtered_points.InsertNextPoint(self._global_current_tip)
        output_block = vtk.vtkUnstructuredGrid()
        output_block.SetPoints(filtered_points)
        cell_ids = vtk.vtkIdList()
        cell_ids.InsertNextId(0)
        output_block.InsertNextCell(vtk.VTK_VERTEX, cell_ids)

        output_data.ShallowCopy(output_block)

        return 1
