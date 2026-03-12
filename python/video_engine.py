"""
ai.play video engine — ai.video(yes)
Text-to-video generation (Sora-style).
Local-first: tries available open-source models in order.
No external API calls.
"""

import os
import time
import tempfile

def generate_video(prompt, duration_seconds=4, fps=8, output_path=None):
    """
    Generate a video from a text prompt.
    Tries available backends in order of quality.
    Returns path to output video file, or None on failure.
    """
    if output_path is None:
        output_path = f'aiplay_video_{int(time.time())}.mp4'

    print(f"[ai.play] Generating video: {prompt[:60]}...")

    # 1. Try ModelScope text-to-video (open source, runs locally)
    result = _try_modelscope(prompt, output_path, duration_seconds, fps)
    if result:
        return result

    # 2. Try zeroscope_v2 via diffusers
    result = _try_zeroscope(prompt, output_path, duration_seconds, fps)
    if result:
        return result

    # 3. Try AnimateDiff via diffusers
    result = _try_animatediff(prompt, output_path, fps)
    if result:
        return result

    # 4. Stub — generate a placeholder video with frames
    result = _generate_stub_video(prompt, output_path, duration_seconds, fps)
    return result


def _try_modelscope(prompt, output_path, duration, fps):
    try:
        from modelscope.pipelines import pipeline
        from modelscope.outputs import OutputKeys
        p = pipeline('text-to-video-synthesis', 'damo/text-to-video-synthesis')
        result = p({'text': prompt})
        frames = result[OutputKeys.OUTPUT_VIDEO]
        _frames_to_mp4(frames, output_path, fps)
        print(f"[ai.play] Video saved: {output_path}")
        return output_path
    except ImportError:
        return None
    except Exception as e:
        print(f"[ai.play] ModelScope video failed: {e}")
        return None


def _try_zeroscope(prompt, output_path, duration, fps):
    try:
        import torch
        from diffusers import DiffusionPipeline
        from diffusers.utils import export_to_video

        pipe = DiffusionPipeline.from_pretrained(
            'cerspense/zeroscope_v2_576w',
            torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32
        )
        pipe = pipe.to('cuda' if torch.cuda.is_available() else 'cpu')
        pipe.enable_model_cpu_offload()

        num_frames = duration * fps
        video_frames = pipe(prompt, num_frames=num_frames, num_inference_steps=20).frames[0]
        export_to_video(video_frames, output_path, fps=fps)
        print(f"[ai.play] Video saved: {output_path}")
        return output_path
    except ImportError:
        return None
    except Exception as e:
        print(f"[ai.play] Zeroscope video failed: {e}")
        return None


def _try_animatediff(prompt, output_path, fps):
    try:
        import torch
        from diffusers import AnimateDiffPipeline, MotionAdapter, EulerDiscreteScheduler
        from diffusers.utils import export_to_gif
        from huggingface_hub import hf_hub_download

        adapter = MotionAdapter.from_pretrained(
            'guoyww/animatediff-motion-adapter-v1-5-2',
            torch_dtype=torch.float16
        )
        pipe = AnimateDiffPipeline.from_pretrained(
            'emilianJR/epiCRealism',
            motion_adapter=adapter,
            torch_dtype=torch.float16
        ).to('cuda' if torch.cuda.is_available() else 'cpu')

        output = pipe(prompt=prompt, num_frames=16, guidance_scale=7.5, num_inference_steps=20)
        frames = output.frames[0]

        # Save as gif then convert
        gif_path = output_path.replace('.mp4', '.gif')
        export_to_gif(frames, gif_path)

        # Convert gif to mp4 if ffmpeg available
        try:
            import subprocess
            subprocess.run(['ffmpeg', '-i', gif_path, '-movflags', 'faststart',
                           '-pix_fmt', 'yuv420p', output_path, '-y'],
                          capture_output=True, timeout=60)
            os.remove(gif_path)
            return output_path
        except Exception:
            return gif_path

    except ImportError:
        return None
    except Exception as e:
        print(f"[ai.play] AnimateDiff failed: {e}")
        return None


def _frames_to_mp4(frames, output_path, fps):
    try:
        import cv2
        import numpy as np
        h, w = frames[0].shape[:2]
        out = cv2.VideoWriter(output_path, cv2.VideoWriter_fourcc(*'mp4v'), fps, (w, h))
        for f in frames:
            out.write(cv2.cvtColor(np.array(f), cv2.COLOR_RGB2BGR))
        out.release()
    except Exception:
        pass


def _generate_stub_video(prompt, output_path, duration, fps):
    """
    Generate a minimal placeholder video — coloured frames with text.
    Used when no video generation backend is available.
    Requires: pip install opencv-python
    """
    try:
        import cv2
        import numpy as np

        w, h = 576, 320
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(output_path, fourcc, fps, (w, h))

        total_frames = int(duration * fps)
        colours = [
            (30, 20, 60), (20, 30, 70), (40, 20, 80),
            (20, 40, 60), (50, 20, 70),
        ]

        for i in range(total_frames):
            frame = np.zeros((h, w, 3), dtype=np.uint8)
            bg = colours[i % len(colours)]
            frame[:] = bg

            # Animated gradient
            t = i / total_frames
            for y in range(h):
                intensity = int(40 + 30 * abs(math.sin(y * 0.05 + t * 6)))
                frame[y] = [min(255, bg[0]+intensity//3),
                             min(255, bg[1]+intensity//4),
                             min(255, bg[2]+intensity//2)]

            # Text overlay
            words = prompt.split()
            line1 = ' '.join(words[:6])
            line2 = ' '.join(words[6:12]) if len(words) > 6 else ''
            cv2.putText(frame, line1, (20, h//2-20),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (220,220,255), 1, cv2.LINE_AA)
            if line2:
                cv2.putText(frame, line2, (20, h//2+20),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200,200,240), 1, cv2.LINE_AA)
            cv2.putText(frame, 'ai.play video', (20, h-20),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.4, (120,120,180), 1, cv2.LINE_AA)
            out.write(frame)

        out.release()
        print(f"[ai.play] Placeholder video saved: {output_path}")
        print(f"[ai.play] Install 'diffusers torch' for real video generation")
        return output_path
    except ImportError:
        print(f"[ai.play] Video generation: install 'opencv-python diffusers torch'")
        return None
    except Exception as e:
        print(f"[ai.play] Video stub failed: {e}")
        return None

import math
