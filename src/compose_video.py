"""Compose the Blender render, reference excerpt, bilingual captions and sound."""
import argparse
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/'output'
OUT.mkdir(exist_ok=True)


def run(argv):
    subprocess.run(['ffmpeg', '-hide_banner', '-loglevel', 'warning', '-y', *argv], check=True)


def stamp(t):
    minutes, seconds = divmod(t,60)
    return f'0:{int(minutes):02}:{seconds:05.2f}'


def captions(path, offset=0, original=False):
    header='''[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1080
WrapStyle: 0
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Label,Arial,24,&H00E8F2F5,&H00FFFFFF,&H8020281B,&H4020281B,0,0,0,0,100,100,2,0,1,1,0,7,42,42,36,1
Style: Hook,Arial,42,&H00E5F2FF,&H00FFFFFF,&H00212920,&H8020281B,-1,0,0,0,100,100,0,0,1,2,1,8,42,42,74,1
Style: Speech,PingFang SC,51,&H00F0F7FF,&H00FFFFFF,&H0021271C,&H8020281B,-1,0,0,0,100,100,0,0,1,3,1,2,36,36,64,1
Style: Small,Arial,22,&H00D7E7F1,&H00FFFFFF,&H0021271C,&H8020281B,0,0,0,0,100,100,1.6,0,1,1.5,0,2,36,36,36,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
'''
    events=[]
    def add(start,end,style,text):events.append(f'Dialogue: 0,{stamp(start)},{stamp(end)},{style},,0,0,0,,{text}')
    if original:
        add(0,3,'Label','THE ORIGINAL  /  NIU LAI')
        add(0,3,'Hook','I asked GPT-6 to recreate this.')
        add(0,1.8,'Speech','妈妈！');add(0,1.8,'Small','MAMA!')
        add(1.8,3,'Speech','牛来！');add(1.8,3,'Small','NIU LAI!')
    o=offset
    add(o,o+14,'Label','GPT-6 × BLENDER  /  3D RECREATION')
    add(o+.35,o+3.25,'Speech','妈妈——！');add(o+.35,o+3.25,'Small','MAMA!')
    add(o+4.65,o+5.5,'Speech','牛来！');add(o+4.65,o+5.5,'Small','NIU LAI!')
    add(o+5.75,o+8.15,'Hook','Then I moved the camera.')
    add(o+8.15,o+11.0,'Small','SAME SCENE. ANOTHER ANGLE.')
    add(o+12.35,o+14,'Speech','妈妈——！');add(o+12.35,o+14,'Small','MAMA!')
    path.write_text(header+'\n'.join(events)+'\n')


def main():
    p=argparse.ArgumentParser();p.add_argument('--fps',type=int,choices=[24],default=24);opt=p.parse_args()
    missing=[f'frame_{i:04d}.png' for i in range(1,337) if not (ROOT/'renders'/f'frame_{i:04d}.png').is_file()]
    if missing:
        raise SystemExit(f'Missing {len(missing)} rendered frames. Run npm run render first.')
    render=OUT/'render-silent.mp4'
    run(['-framerate',str(opt.fps),'-i',str(ROOT/'renders/frame_%04d.png'),'-c:v','libx264','-preset','medium','-crf','18','-pix_fmt','yuv420p','-movflags','+faststart',str(render)])
    # One unchanged excerpt under the recreation; the final cry is an intentional replay.
    run(['-i',str(ROOT/'web/assets/dialogue.m4a'),'-filter_complex',
         '[0:a]asplit=2[a][b];[a]apad=whole_dur=14[a0];[b]atrim=start=0.4:end=2.15,asetpts=PTS-STARTPTS,adelay=12250|12250[b0];[a0][b0]amix=inputs=2:normalize=0,atrim=duration=14[out]',
         '-map','[out]','-c:a','aac','-b:a','192k',str(OUT/'recreation-audio.m4a')])
    run(['-i',str(render),'-i',str(OUT/'recreation-audio.m4a'),'-map','0:v','-map','1:a','-c:v','copy','-c:a','copy','-t','14','-movflags','+faststart',str(OUT/'recreation-raw.mp4')])
    ref=ROOT/'reference/movie-excerpt.mp4'
    run(['-i',str(ref),'-filter_complex',
         '[0:v]split=2[v1][v2];[0:a]asplit=2[a1][a2];'
         '[v1]trim=start=4.8:end=6.6,setpts=PTS-STARTPTS,crop=720:720:0:230,scale=1080:1080,fps=24,setsar=1[v1o];'
         '[v2]trim=start=8.35:end=9.55,setpts=PTS-STARTPTS,crop=720:720:0:230,scale=1080:1080,fps=24,setsar=1[v2o];'
         '[a1]atrim=start=4.8:end=6.6,asetpts=PTS-STARTPTS[a1o];'
         '[a2]atrim=start=8.35:end=9.55,asetpts=PTS-STARTPTS[a2o];'
         '[v1o][a1o][v2o][a2o]concat=n=2:v=1:a=1[v][a]',
         '-map','[v]','-map','[a]','-c:v','libx264','-crf','18','-pix_fmt','yuv420p','-c:a','aac','-ar','48000','-t','3',str(OUT/'reference-intro.mp4')])
    captions(OUT/'twitter-captions.ass',3,True)
    captions(OUT/'recreation-captions.ass')
    for name,seconds in [('twitter',17),('recreation',14)]:
        subprocess.run(['node',str(ROOT/'src/caption_frames.mjs'),str(OUT/(name+'-captions.ass')),str(ROOT/'renders'/(name+'-captions')),str(seconds)],check=True)
    run(['-i',str(OUT/'reference-intro.mp4'),'-i',str(OUT/'recreation-raw.mp4'),'-framerate','24','-i',str(ROOT/'renders/twitter-captions/caption_%04d.png'),'-filter_complex',
         '[0:v][0:a][1:v][1:a]concat=n=2:v=1:a=1[v][a];[v][2:v]overlay=shortest=1[out]',
         '-map','[out]','-map','[a]','-c:v','libx264','-preset','medium','-crf','18','-pix_fmt','yuv420p','-c:a','aac','-b:a','192k','-movflags','+faststart',str(OUT/'niulai-twitter.mp4')])
    run(['-i',str(OUT/'recreation-raw.mp4'),'-framerate','24','-i',str(ROOT/'renders/recreation-captions/caption_%04d.png'),'-filter_complex','[0:v][1:v]overlay=shortest=1[out]','-map','[out]','-map','0:a',
         '-c:v','libx264','-crf','18','-pix_fmt','yuv420p','-c:a','copy','-movflags','+faststart',str(OUT/'niulai-3d.mp4')])
    print('VIDEO_EXPORT_COMPLETE',OUT/'niulai-twitter.mp4')


if __name__=='__main__':main()
