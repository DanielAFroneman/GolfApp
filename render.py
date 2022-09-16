from json import load
import torch

from pytorch3d.io import load_obj
from pytorch3d.structures import Meshes, join_meshes_as_batch
from pytorch3d.transforms import RotateAxisAngle, quaternion_to_matrix, Rotate
from pytorch3d.renderer import(
    look_at_view_transform,
    FoVPerspectiveCameras,
    Materials,
    RasterizationSettings,
    MeshRenderer,
    MeshRasterizer,
    SoftPhongShader,
    HardFlatShader,
    TexturesVertex,
    TexturesAtlas,
    PointsRenderer,
    PointsRasterizationSettings,
    PointsRasterizer,
    PointLights
)

from skimage.io import imread

class Obj_Renderer:
    def __init__(self, filepath) -> None:
        self.device = torch.device("cpu")

        self.verts, self.faces, aux = load_obj(
            filepath,
            device=self.device,
            load_textures=True,
            create_texture_atlas=True,
            texture_atlas_size=4,
            texture_wrap="repeat"
        )

        self.atlas = aux.texture_atlas

        self.raster_settings = RasterizationSettings(
            image_size=512,
            blur_radius=0,
            faces_per_pixel=1,
            bin_size=None
        )

        self.lights = PointLights(
            device=self.device, 
            location=[[0.0, 0.0, -10.0]]
        )

    def render_image(self, rotations):
        batch_size = len(rotations)

        
        matrixList = [torch.as_tensor(rot) for rot in rotations]

        # quartRotations = [torch.tensor([q[0][0], q[1][0], q[2][0], q[3][0]]) for q in rotations]

        R, T = look_at_view_transform(
            dist=10,
            elev=10,
            azim=0
        )

        cameras = FoVPerspectiveCameras(
            device=self.device,
            R=R,
            T=T
        )

        rasterizer = MeshRasterizer(
            cameras=cameras,
            raster_settings=self.raster_settings
        )

        shader = HardFlatShader(
            device=self.device,
            cameras=cameras
        )

        # shader = SoftPhongShader(
        #     device=self.device,
        #     cameras=cameras,
        #     lights=self.lights
        # )

        renderer = MeshRenderer(
            rasterizer=rasterizer,
            shader=shader
        )

        # matrixlist = [quaternion_to_matrix(quart) for quart in quartRotations]
        rotlist = [Rotate(matrix, device=self.device) for matrix in matrixList]
        vertlist = [rot.transform_points(self.verts) for rot in rotlist]
        meshlist = [Meshes(verts=[verts], faces=[self.faces.verts_idx],textures=TexturesAtlas(atlas=[self.atlas])) for verts in vertlist]

        # rotlist = [RotateAxisAngle(rotation,'Y', device=self.device) for rotation in rotations]
        # vertlist = [rot_y.transform_points(self.verts) for rot_y in rotlist]
        # meshlist = [Meshes(verts=[verts], faces=[self.faces.verts_idx],textures=TexturesAtlas(atlas=[self.atlas])) for verts in vertlist]

        images = [renderer(capsule_mesh)[0, ..., :3].squeeze().cpu() for capsule_mesh in meshlist]


        return images
