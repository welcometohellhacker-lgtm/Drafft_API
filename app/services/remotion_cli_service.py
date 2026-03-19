import subprocess
from pathlib import Path


class RemotionCliService:
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.renderer_root = project_root / 'remotion_renderer'

    def render(self, composition: str, props_path: str, output_path: str, thumb_path: str) -> dict:
        cmd = [
            'node',
            'render.mjs',
            '--composition', composition,
            '--props', props_path,
            '--out', output_path,
            '--thumb', thumb_path,
        ]
        proc = subprocess.run(cmd, cwd=self.renderer_root, capture_output=True, text=True)
        if proc.returncode != 0:
            raise RuntimeError(proc.stderr or proc.stdout or 'Remotion render failed')
        return {
            'stdout': proc.stdout.strip(),
            'stderr': proc.stderr.strip(),
            'output_path': output_path,
            'thumbnail_path': thumb_path,
        }
