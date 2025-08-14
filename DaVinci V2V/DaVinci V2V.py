# ================= 用户配置 =================
SCRIPT_NAME = "DaVinci V2V"
SCRIPT_VERSION = " 1.0"
SCRIPT_AUTHOR = "HEIBA"

SCREEN_WIDTH, SCREEN_HEIGHT = 1920, 1080
WINDOW_WIDTH, WINDOW_HEIGHT = 300, 410
X_CENTER = (SCREEN_WIDTH - WINDOW_WIDTH) // 2
Y_CENTER = (SCREEN_HEIGHT - WINDOW_HEIGHT) // 2

SCRIPT_KOFI_URL="https://ko-fi.com/heiba"
SCRIPT_BILIBILI_URL  = "https://space.bilibili.com/385619394"
AI_TRANSLATOR_KOFI_URL         = "https://ko-fi.com/s/706feb3730"
AI_TRANSLATOR_TAOBAO_URL       = "https://item.taobao.com/item.htm?id=941978471966&pisk=gmixjtVnkLBAk6oYEx8lsCfgBuJoDUD42jkCj5Vc5bh-CjN0srasFYw3hsw_CAw_XbGM3SD6gfnTNoaZo5V06lHZ9LAHxHDq3lrXtBxhSo87Vk5_CP1GNzwTX-iubvUx3lr6tTj6-HHqgqUTVGw_FLegIs1s1rt7F7yFhlNb5__7d7Z_frafV_wUKisbGS9JVJyOhss_1_Z7nJb_flGsFLeaN-Z_fUXJ676bsG3h-ZNfaUaffGi8HzTon7tqd0wx7WHjDGs67-UYOxNJGOnwyPhYk0xAT-3Spbyx_HS4cP3jRoi99nESL4cbefOdW7gK0cUnDBQUGmPZ9ogJNiE_0JHT-4v1J70sU0U-DeXaUmDs0yqBYsNirvnTBcRw2XHjM2aIcsIPyDmLlof39RbXeLQN7rwPjSA3qzqXeBe8tKKO7NzyU8FHeLQN7rwzeWvvXN7azL5..&spm=a21xtw.29178619.0.0"
WHISPER_KOFI_URL = "https://ko-fi.com/s/da133415d5"
WHISPER_TAOBAO_URL = "https://item.taobao.com/item.htm?ft=t&id=959855444978"
RUNWAY_REGISTER_URL ="https://dev.runwayml.com/login"

import os
import sys
import platform
import re
import time
import wave
import json
import base64
import mimetypes
import requests
import webbrowser
from xml.dom import minidom
import xml.etree.ElementTree as ET
from typing import Dict, Any, List, Optional

SCRIPT_PATH = os.path.dirname(os.path.abspath(sys.argv[0]))
TEMP_DIR = os.path.join(SCRIPT_PATH, "video_temp")
SETTINGS = os.path.join(SCRIPT_PATH, "config", "settings.json")
DEFAULT_SETTINGS = {

    "RUNWAY_BASE_URL": "",
    "RUNWAY_API_KEY": "",
    "PATH":"",
    "SEED":"",
    "SEED_RANDOM": True, 
    "RATIO":0,
    "MODEL": 0,
    "CN":True,
    "EN":False,
}

ui = fusion.UIManager
dispatcher = bmd.UIDispatcher(ui)
loading_win = dispatcher.AddWindow(
    {
        "ID": "LoadingWin",                            
        "WindowTitle": "Loading",                     
        "Geometry": [X_CENTER, Y_CENTER, WINDOW_WIDTH, WINDOW_HEIGHT],                  
        "Spacing": 10,                                
        "StyleSheet": "*{font-size:14px;}"            
    },
    [
        ui.VGroup(                                  
            [
                ui.Label(                          
                    {
                        "ID": "LoadLabel", 
                        "Text": "Loading...",
                        "Alignment": {"AlignHCenter": True, "AlignVCenter": True},
                    }
                )
            ]
        )
    ]
)
loading_win.Show()

# ================== DaVinci Resolve 接入 ==================
try:
    import DaVinciResolveScript as dvr_script
    from python_get_resolve import GetResolve
    print("DaVinciResolveScript from Python")
except ImportError:
    # mac / windows 常规路径补全
    if platform.system() == "Darwin": 
        path1 = "/Library/Application Support/Blackmagic Design/DaVinci Resolve/Developer/Scripting/Examples"
        path2 = "/Library/Application Support/Blackmagic Design/DaVinci Resolve/Developer/Scripting/Modules"
    elif platform.system() == "Windows":
        path1 = os.path.join(os.environ['PROGRAMDATA'], "Blackmagic Design", "DaVinci Resolve", "Support", "Developer", "Scripting", "Examples")
        path2 = os.path.join(os.environ['PROGRAMDATA'], "Blackmagic Design", "DaVinci Resolve", "Support", "Developer", "Scripting", "Modules")
    else:
        raise EnvironmentError("Unsupported operating system")
    sys.path += [path1, path2]
    import DaVinciResolveScript as dvr_script
    from python_get_resolve import GetResolve
    print("DaVinciResolveScript from DaVinci")

def connect_resolve():
    project_manager = resolve.GetProjectManager()
    proj = project_manager.GetCurrentProject()
    media_pool = proj.GetMediaPool(); 
    root_folder = media_pool.GetRootFolder()
    timeline      = proj.GetCurrentTimeline()
    fps     = float(proj.GetSetting("timelineFrameRate"))
    return resolve, proj, media_pool,root_folder,timeline, fps

def add_v2v_marker():
    resolve, proj, mpool, root, tl, fps = connect_resolve()
    marker_frame = 0
    #print(marker_frame)
    marker_name = "Render Marker" 
    marker_note = "Drag the marker to set the rendering range" 
    marker_date = "v2v"
    marker_color = "Yellow"
    marker_duration = 125

    tl.DeleteMarkerAtFrame(marker_frame)
    success = tl.AddMarker(
        marker_frame,
        marker_color,
        marker_name,
        marker_note,
        marker_duration,
        marker_date
    )
    print("✅ Marker added successfully!" if success else "❌ Failed to add marker, please check if the frameId or other parameters are correct.")

add_v2v_marker()

def render_video_by_marker(output_dir: str, custom_name: str, ratio: str) -> Optional[str]:
    resolve, proj, mpool, root, tl, fps = connect_resolve()
    render_preset = f"render_{ratio.replace(':', 'x')}"
    resolve.ImportRenderPreset(os.path.join(SCRIPT_PATH, "render_preset", f"{render_preset}.xml"))
    proj.LoadRenderPreset(render_preset)
    proj.SetCurrentRenderFormatAndCodec("mp4", "H.264")
    markers = tl.GetMarkers() or {}
    v2v_frames = [f for f, m in markers.items() if m.get("customData") == "v2v"]
    if not v2v_frames:
        print("No V2V markers found.")
        return None
    first_frame_id = sorted(v2v_frames)[0]
    marker_info = markers[first_frame_id]
    local_start = int(first_frame_id)
    local_end   = local_start + int(marker_info["duration"]) - 1
    timeline_start_frame = tl.GetStartFrame()
    mark_in  = timeline_start_frame + local_start
    mark_out = timeline_start_frame + local_end
    settings = {
        "MarkIn": mark_in,
        "MarkOut": mark_out,
        "TargetDir": output_dir,
        "CustomName": custom_name,
        "ExportVideo": True,
        "ExportAudio": False,
        "SelectAllFrames": False,  # 只渲染 Mark 区域
    }
    proj.SetRenderSettings(settings)
    job_id = proj.AddRenderJob()
    if not job_id:
        print("添加渲染任务失败")
        return None

    if not proj.StartRendering(job_id):
        print("渲染启动失败")
        return None
    import time
    while proj.IsRenderingInProgress():
        print("Rendering...")
        time.sleep(0.5)  
    resolve.OpenPage("edit")
    render_file = os.path.join(output_dir, custom_name + ".mp4")
    return render_file

def get_first_empty_track(timeline, start_frame, end_frame, media_type):
    """获取当前播放头位置的第一个空轨道索引"""
    track_index = 1
    while True:
        runway_items = timeline.GetItemListInTrack(media_type, track_index)
        if not runway_items:
            return track_index
        
        # 检查轨道上是否有片段与给定的start_frame和end_frame重叠
        is_empty = True
        for item in runway_items:
            if item.GetStart() <= end_frame and start_frame <= item.GetEnd():
                is_empty = False
                break
        
        if is_empty:
            return track_index
        
        track_index += 1

def timecode_to_frames(timecode, frame_rate):
    """
    将时间码转换为帧数。
    参数：
    - timecode: 格式为 'hh:mm:ss;ff' 或 'hh:mm:ss:ff' 的时间码。
    - frame_rate: 时间线的帧率。
    返回值：
    - 对应时间码的帧数。
    """
    try:
        # 提取时间组件
        match = re.match(r"^(\d{2}):(\d{2}):(\d{2})([:;])(\d{2,3})$", timecode)
        if not match:
            raise ValueError(f"Invalid timecode format: {timecode}")
        
        hours, minutes, seconds, separator, frames = match.groups()
        hours = int(hours)
        minutes = int(minutes)
        seconds = int(seconds)
        frames = int(frames)
        
        is_drop_frame = separator == ';'
        
        if is_drop_frame:
            if frame_rate in [23.976, 29.97, 59.94, 119.88]:
                nominal_frame_rate = round(frame_rate * 1000 / 1001)
                drop_frames = int(round(nominal_frame_rate / 15))
            else:
                raise ValueError(f"Unsupported drop frame rate: {frame_rate}")
            total_minutes = hours * 60 + minutes

            total_dropped_frames = drop_frames * (total_minutes - total_minutes // 10)

            frame_count = ((hours * 3600) + (minutes * 60) + seconds) * nominal_frame_rate + frames
            frame_count -= total_dropped_frames

        else:
            if frame_rate in [23.976, 29.97, 47.952, 59.94, 95.904, 119.88]:
                nominal_frame_rate = round(frame_rate * 1000 / 1001)
            else:
                nominal_frame_rate = frame_rate

            frame_count = ((hours * 3600) + (minutes * 60) + seconds) * nominal_frame_rate + frames

        return frame_count

    except ValueError as e:
        print(f"Error converting timecode to frames: {e}")
        return None
    
def add_to_media_pool_and_timeline(start_frame, end_frame, filename):
    resolve, proj, mpool, root, tl, fps = connect_resolve()
    media_pool = proj.GetMediaPool()
    root_folder = media_pool.GetRootFolder()
    v2v_folder = None

    folders = root_folder.GetSubFolderList()
    for folder in folders:
        if folder.GetName() == "V2V":
            v2v_folder = folder
            break

    if not v2v_folder:
        v2v_folder = media_pool.AddSubFolder(root_folder, "V2V")

    if v2v_folder:
        print(f"V2V folder is available: {v2v_folder.GetName()}")
    else:
        print("Failed to create or find V2V folder.")
        return False

    media_pool.SetCurrentFolder(v2v_folder)
    imported_items = media_pool.ImportMedia([filename])
    
    if not imported_items:
        print(f"Failed to import media: {filename}")
        return False

    selected_clip = imported_items[0]
    print(f"Imported clip: {selected_clip.GetName()}")

    clip_duration_frames = timecode_to_frames(selected_clip.GetClipProperty("Duration"), fps)

    track_index = get_first_empty_track(tl, start_frame, end_frame, "video")

    clip_info = {
        "mediaPoolItem": selected_clip,
        "startFrame": 0,
        "endFrame": clip_duration_frames - 1,
        "trackIndex": track_index,
        "recordFrame": start_frame,  # 在字幕的起始位置添加
        "stereoEye": "both"  # 设置为立体声
    }

    timeline_item = media_pool.AppendToTimeline([clip_info])
    if timeline_item:
        
        print(f"Appended clip: {selected_clip.GetName()} to timeline at frame {start_frame} on track {track_index}.")
        return True
    else:
        print("Failed to append clip to timeline.")

def generate_filename(base_path, prompt, extension):
    if not os.path.exists(base_path):
        os.makedirs(base_path)
    clean_prompt = prompt.replace('\n', ' ').replace('\r', ' ')
    clean_prompt = re.sub(r'[<>:"/\\|?*]', '', clean_prompt)
    clean_prompt = clean_prompt[:15]
    count = 0
    while True:
        count += 1
        filename = f"{base_path}/{clean_prompt}#{count}{extension}"
        if not os.path.exists(filename):
            return filename 
        

def load_settings(settings_file):
    if os.path.exists(settings_file):
        with open(settings_file, 'r') as file:
            content = file.read()
            if content:
                try:
                    settings = json.loads(content)
                    return settings
                except json.JSONDecodeError as err:
                    print('Error decoding settings:', err)
                    return None
    return None

class BaseProvider:
    """所有服务商的基类，约定统一方法签名。"""
    def video_to_video(self, video_path: str, **kwargs): raise NotImplementedError
    def get_task_status(self, task_id: str, save_path: str | None = None): raise NotImplementedError

class RunwayProvider(BaseProvider):
    # —— 类变量（常量） ——  
    MODEL = [
        "gen4_aleph"
    ]
    ACCEPTED_RATIOS = [
        "1280:720","720:1280","1104:832","960:960",
        "832:1104","1584:672","848:480","640:480"
    ]

    BASE_URL = "https://api.dev.runwayml.com"

    def __init__(self, base_url: str , api_key: str):
        self.base_url = base_url.strip().rstrip('/') or self.BASE_URL
        self.api_key = api_key
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "X-Runway-Version": "2024-11-06",
            "Content-Type": "application/json"
        }

    @staticmethod
    def _file_to_data_uri(filepath: str) -> str:
        mime, _ = mimetypes.guess_type(filepath)
        mime = mime or "application/octet-stream"
        with open(filepath, "rb") as f:
            b64 = base64.b64encode(f.read()).decode()
        return f"data:{mime};base64,{b64}"

    def video_to_video(
        self,
        video_path: str,
        prompt: str,
        model: str,
        ratio: str,
        seed: int | None = None,
        references: list | None = None,
        public_figure_threshold: str = "low"
    ) -> str | None:
        # —— 使用类常量做校验 ——  
        if model not in self.MODEL:
            print(f"[Runway] model 必须为 {self.MODEL}，已收到: {model}")
            return None

        if ratio not in self.ACCEPTED_RATIOS:
            print(f"[Runway] ratio 必须是以下之一: {self.ACCEPTED_RATIOS}，已收到: {ratio}")
            return None

        payload = {
            "videoUri"          : self._file_to_data_uri(video_path),
            "promptText"        : prompt,
            "model"             : model,
            "ratio"             : ratio,
            "contentModeration" : {"publicFigureThreshold": public_figure_threshold}
        }

        if seed is not None:        payload["seed"]       = seed
        if references is not None:  payload["references"] = references
        try:
            r = requests.post(
                f"{self.base_url}/v1/video_to_video",
                headers=self.headers,
                json=payload,
                timeout=300
            )
            r.raise_for_status()
            return r.json().get("id")
        except Exception as e:
            if hasattr(e, 'response') and e.response is not None:
                print(f"[{e.response.status_code}] {e.response.text}")
                show_dynamic_message(f"[Runway] Failed: {e.response.text}", f"[Runway] 失败: {e.response.text}")
            else:
                print(f"[Runway] An unexpected error occurred: {e}")
                show_dynamic_message(f"[Runway] Failed: {e}", f"[Runway] 失败: {e}")
            print(f"[Runway] video_to_video 失败: {e}")
            return None

    def get_task_status(
        self,
        task_id: str,
        poll_interval: int = 1,
        timeout: int = 300
    ) -> str | None:
        """
        轮询任务直至 SUCCEEDED / FAILED / 超时。
        成功返回输出 URL；失败或超时返回 None。
        **所有官方状态都会打印**，方便调试。
        """
        start_ts = time.time()
        while True:
            try:
                r = requests.get(
                    f"{self.base_url}/v1/tasks/{task_id}",
                    headers=self.headers,
                    timeout=30
                )
                r.raise_for_status()
                info   = r.json()
                status = info.get("status")
                elapsed = int(time.time() - start_ts)

                if status == "PENDING":
                    show_dynamic_message(f"[Runway] PENDING…{elapsed}s", f"[Runway] 正在排队…{elapsed}s")
                    print(f"[Runway] {task_id} PENDING…{elapsed}s")
                elif status == "RUNNING":
                    raw_prog = info.get("progress", 0.0)
                    try:
                        prog = float(raw_prog)  
                    except (TypeError, ValueError):
                        prog = 0.0
                    pct = f"{prog * 100:.1f}%"
                    show_dynamic_message(f"[Runway] RUNNING... {pct}, {elapsed}s",
                                        f"[Runway] 生成中... {pct}，{elapsed}s")
                    print(f"[Runway] {task_id} RUNNING...{pct}，{elapsed}s")
                elif status == "THROTTLED":
                    show_dynamic_message(f"[Runway] THROTTLED, waiting... {elapsed}s",
                                         f"[Runway] 被限流，等待重试... {elapsed}s")
                    print(f"[Runway] {task_id} THROTTLED...{elapsed}s")
                elif status == "SUCCEEDED":
                    url = (info.get("output") or info.get("outputs") or None)
                    if isinstance(url, list):   # 兼容 "output": [...]
                        url = url[0]
                    show_dynamic_message(f"[Runway] SUCCEEDED → {elapsed}s",
                                         f"[Runway] 成功 → {elapsed}s")
                    print(f"[Runway] {task_id} SUCCEEDED → {elapsed}s")
                    return url
                elif status == "FAILED":
                    show_dynamic_message(f"[Runway] FAILED → {elapsed}s", f"[Runway] 失败 → {elapsed}s")
                    print(f"[Runway] {task_id} FAILED → "
                          f"{info.get('failure')} (code={info.get('failureCode')})")
                    return None
                else:
                    show_dynamic_message(f"[Runway] FAILED → {elapsed}s", f"[Runway] 失败 → {elapsed}s")
                    print(f"[Runway] {task_id} status: {status}")

                if time.time() - start_ts >= timeout:
                    show_dynamic_message(f"[Runway] TIMEOUT → {elapsed}s", f"[Runway] 超时 → {elapsed}s")
                    print(f"[Runway] {task_id} timeout ({timeout}s)")
                    return None

                time.sleep(poll_interval)

            except Exception as e:
                show_dynamic_message(f"[Runway] 查询任务状态异常: {e}", f"[Runway] 查询任务状态异常: {e}")
                print(f"[Runway] 查询任务状态异常: {e}")
                return None
            
    def download_file(
        self, url: str, 
        save_path: str, 
        chunk_size: int = 8192,
        timeout_secs: int = 300   # 新增：总超时（秒），默认 5 分钟
    ) -> str | None:
        try:
            parent = os.path.dirname(save_path)
            if parent:
                os.makedirs(parent, exist_ok=True)

            start_ts = time.time()  # 新增：记录开始时间

            # 你原先的 120 秒 read 超时会被总超时兜底；也可以改为 (连接超时, 读取超时) 元组
            with requests.get(url, stream=True, timeout=120) as resp:
                resp.raise_for_status()

                total_size = int(resp.headers.get("Content-Length", 0))  # 可能为 0
                downloaded = 0
                last_pct   = -1
                last_time  = time.time()

                with open(save_path, "wb") as f:
                    for chunk in resp.iter_content(chunk_size):
                        if time.time() - start_ts >= timeout_secs:
                            show_dynamic_message("[Runway] Download timeout (300s). Canceled.",
                                                "[Runway] 下载超时（300秒），已取消。")
                            try:
                                f.close()
                            except Exception:
                                pass
                            try:
                                if os.path.exists(save_path):
                                    os.remove(save_path)
                            except Exception:
                                pass
                            return None

                        if not chunk:
                            continue

                        f.write(chunk)
                        downloaded += len(chunk)

                        # —— 进度汇报 —— #
                        if total_size:  # 有总长度 ⇒ 百分比
                            pct = int(downloaded * 100 / total_size)
                            if pct != last_pct:
                                show_dynamic_message(f"[Runway] Downloading: {pct}%",
                                                    f"[Runway] 下载进度: {pct}%")
                                print(f"[Runway] Downloading: {pct}%")
                                last_pct = pct
                        else:  # 无总长度 ⇒ 已下载 MB
                            if time.time() - last_time >= 0.5:
                                mb = downloaded / (1024 * 1024)
                                show_dynamic_message(f"[Runway] Downloaded {mb:.1f} MB",
                                                    f"[Runway] 已下载 {mb:.1f} MB")
                                print(f"[Runway] Downloaded {mb:.1f} MB")
                                last_time = time.time()

            # 下载完成
            show_dynamic_message("[Runway] File saved → " + save_path,
                                "[Runway] 文件已保存 → " + save_path)
            print(f"[Runway] 文件已保存 → {save_path}")
            return True

        except Exception as e:
            print(f"[Runway] 下载失败: {e}")
            return None

        
v2v_win = dispatcher.AddWindow(
    {
        "ID": 'RunwayWin',
        "WindowTitle": SCRIPT_NAME + SCRIPT_VERSION,
        "Geometry": [X_CENTER, Y_CENTER, WINDOW_WIDTH, WINDOW_HEIGHT],
        "Spacing": 10,
        "StyleSheet": "*{font-size:14px;}"
    },
    [
        ui.VGroup([
            ui.TabBar({"ID":"MyTabs","Weight":0.0}),
            ui.Stack({"ID":"MyStack","Weight":1.0},[
                ui.VGroup({"Weight":1},[
                    ui.TextEdit({"ID": "Prompt", "Text": "", "PlaceholderText": "Prompt ...", "Weight": 0.4}),
                    ui.HGroup({"Weight":0.1},[
                            ui.Label({"ID":"ModelLabel","Text":"Model:","Weight":0.4}),
                            ui.ComboBox({"ID":"ModelCombo","Weight":0.6}),                    
                        ]),
                    ui.HGroup({"Weight":0.1},[
                            ui.Label({"ID":"RatioLabel","Text":"Ratio:","Weight":0.4}),
                            ui.ComboBox({"ID":"RatioCombo","Weight":0.6}),                    
                        ]),
                    ui.HGroup({"Weight": 0.1}, [
                        ui.Label({"ID":"SeedLabel","Text":"Seed:","Weight":0.4}),
                        ui.LineEdit({"ID": "SeedInput", "Text": "", "PlaceholderText": "","Weight":0.3}),
                        ui.CheckBox({"ID":"RandSeedCheckBox","Text":"Random","Checked": True, "Weight":0.3, "Alignment": {"AlignLeft": True},})
                    ]),
                    ui.HGroup({"Weight":0.1}, [
                            ui.Label({"ID":"RefLabel","Text":"Reference:","Weight":0.4}),
                            ui.Label({"ID":"RefPath","Text":"", "WordWrap": True, "Weight":0.3}),  # 显示所选图片路径
                            ui.Button({"ID":"SelectRefButton","Text":"Select","Weight":0.3})
                        ]),
                    ui.HGroup({"Weight": 0.1}, [
                        ui.Label({"ID":"TaskIDLabel","Text":"Task ID:","Weight":0.4}),
                        ui.LineEdit({"ID": "TaskID", "Text": "", "PlaceholderText": "","Weight":0.6})
                    ]),
                    ui.HGroup({"Weight": 0.1}, [
                        ui.Button({"ID": "PostButton", "Text": "提交任务", "Weight": 0.2}),
                        ui.Button({"ID": "GetButton", "Text": "下载视频", "Weight": 0.2}),
                    ]),
                    
                    
                ]),
                ui.VGroup({"Weight":1},[
                    ui.HGroup({"Weight": 0}, [
                            ui.Label({"ID": "PathLabel", "Text": "保存路径", "Alignment": {"AlignLeft": True}, "Weight": 0.2}),
                            ui.LineEdit({"ID": "Path", "Text": "", "PlaceholderText": "", "ReadOnly": False, "Weight": 0.6}),
                            ui.Button({"ID": "Browse", "Text": "浏览", "Weight": 0.2}),
                        ]),
                    ui.HGroup({"Weight":0},[
                        ui.Label({"ID":"RunwayConfigLabel","Text":"Runway","Weight":0.1}),
                        ui.Button({"ID":"ShowRunway","Text":"配置","Weight":0.1}),
                    ]),
                    ui.HGroup({"Weight": 0}, [
                        ui.CheckBox({"ID":"LangEnCheckBox","Text":"EN","Checked":True,"Weight":0}),
                        ui.CheckBox({"ID":"LangCnCheckBox","Text":"简体中文","Checked":False,"Weight":0}),
                    ]),
                    ui.Button({
                            "ID": "CopyrightButton", 
                            "Text": f"© 2025, Copyright by {SCRIPT_AUTHOR}",
                            "Alignment": {"AlignHCenter": True, "AlignVCenter": True},
                            "Font": ui.Font({"PixelSize": 12, "StyleName": "Bold"}),
                            "Flat": True,
                            "TextColor": [0.1, 0.3, 0.9, 1],
                            "BackgroundColor": [1, 1, 1, 0],
                            "Weight": 0.1
                        })
                ]),
            ]),
            
        ])
    ]
)
runway_config_win = dispatcher.AddWindow(
    {
        "ID": "RunwayConfigWin",
        "WindowTitle": "OpenAI API",
        "Geometry": [900, 400, 350, 150],
        "Hidden": True,
        "StyleSheet": """
        * {
            font-size: 14px; /* 全局字体大小 */
        }
    """
    },
    [
        ui.VGroup(
            [
                ui.Label({"ID": "RunwayLabel","Text": "填写OpenAI API信息", "Alignment": {"AlignHCenter": True, "AlignVCenter": True}}),
                ui.HGroup({"Weight": 1}, [
                    ui.Label({"ID": "RunwayBaseURLLabel", "Text": "Base URL", "Alignment": {"AlignRight": False}, "Weight": 0.2}),
                    ui.LineEdit({"ID": "RunwayBaseURL", "Text":"","PlaceholderText": "https://api.dev.runwayml.com", "Weight": 0.8}),
                ]),
                ui.HGroup({"Weight": 1}, [
                    ui.Label({"ID": "RunwayApiKeyLabel", "Text": "API Key", "Alignment": {"AlignRight": False}, "Weight": 0.2}),
                    ui.LineEdit({"ID": "RunwayApiKey", "Text": "", "EchoMode": "Password", "Weight": 0.8}),
                    
                ]),
                ui.HGroup({"Weight": 1}, [
                    ui.Button({"ID": "RunwayConfirm", "Text": "确定","Weight": 1}),
                    ui.Button({"ID": "RunwayRegisterButton", "Text": "注册","Weight": 1}),
                ]),
                
            ]
        )
    ]
)
msgbox = dispatcher.AddWindow(
        {
            "ID": 'msg',
            "WindowTitle": 'Warning',
            "Geometry": [750, 400, 350, 100],
            "Spacing": 10,
        },
        [
            ui.VGroup(
                [
                    ui.Label({"ID": 'WarningLabel', "Text": "",'Alignment': { 'AlignCenter' : True },'WordWrap': True}),
                    ui.HGroup({"Weight": 0}, [ui.Button({"ID": 'OkButton', "Text": 'OK'})]),
                ]
            ),
        ]
    )
translations = {
    "cn": {
        "Tabs": ["Runway","配置"],
        "ModelLabel":"模型：",
        "SeedLabel":"随机种子：",
        "RefLabel":"参考图：",
        "SelectRefButton":"选择图片",
        "RandSeedCheckBox":"随机",
        "PostButton":"生成",
        "GetButton":"下载视频",
        "TaskIDLabel":"任务ID：",
        "RatioLabel":"比例：",
        "PathLabel":"保存路径",
        "ShowRunway":"配置",
        "Browse":"浏览",
        "RunwayConfigLabel":"Runway",
        "RunwayLabel":"填写 Runway 信息",
        "RunwayBaseURLLabel":"Base URL",
        "RunwayApiKeyLabel":"API KEY",
        "RunwayConfirm":"确定",
        "RunwayRegisterButton":"注册",


        },
    "en": {
        "Tabs": ["Runway","Configuration"],
        "ModelLabel":"Model:",
        "SeedLabel":"Seed:",
        "RefLabel":"Reference:",
        "SelectRefButton":"Select",
        "RandSeedCheckBox":"Random",
        "PostButton":"Generate",
        "GetButton":"Download Video",
        "RatioLabel":"Ratio:",
        "TaskIDLabel":"Task ID:",
        "PathLabel":"Save Path",
        "ShowRunway":"config",
        "Browse":"Browse",
        "RunwayConfigLabel":"Runway",
        "RunwayLabel":"Runway API",
        "RunwayBaseURLLabel":"Base URL",
        "RunwayApiKeyLabel":"API KEY",
        "RunwayConfirm":"Confirm",
        "RunwayRegisterButton":"Register",
        }
}

def show_dynamic_message(en_text, zh_text):
    use_en = runway_items["LangEnCheckBox"].Checked
    msg = en_text if use_en else zh_text
    msgbox.Show()
    msg_items["WarningLabel"].Text = msg

def on_msg_close(ev):
    msgbox.Hide()
msgbox.On.OkButton.Clicked = on_msg_close
msgbox.On.msg.Close = on_msg_close

runway_items       = v2v_win.GetItems()
msg_items = msgbox.GetItems()
runway_config_items = runway_config_win.GetItems()
runway_items["MyStack"].CurrentIndex = 0
runway_items["GetButton"].Enabled = False

for tab_name in translations["cn"]["Tabs"]:
    runway_items["MyTabs"].AddTab(tab_name)

for model in RunwayProvider.MODEL:
    runway_items["ModelCombo"].AddItem(model)

for ratio in RunwayProvider.ACCEPTED_RATIOS:
    runway_items["RatioCombo"].AddItem(ratio)

def on_select_ref_image(ev):
    # 初始目录优先用当前保存路径或脚本路径
    start_dir = runway_items["Path"].Text or SCRIPT_PATH
    try:
        # 只允许选择 jpg/jpeg/png/webp
        selected = fusion.RequestFile(start_dir, ["*.jpg", "*.jpeg", "*.png", "*.webp"])
    except Exception:
        selected = None

    if selected and os.path.exists(selected):
        # 校验 MIME 类型
        mime_type, _ = mimetypes.guess_type(selected)
        allowed_mimes = ["image/jpeg", "image/jpg", "image/png", "image/webp"]

        if mime_type and mime_type.lower() in allowed_mimes:
            # 显示文件名（不显示完整路径）
            runway_items["RefPath"].Text = selected
        else:
            show_dynamic_message("Only JPEG, PNG, WebP images are allowed.",
                                 "仅支持 JPEG、PNG、WebP 图片。")

v2v_win.On.SelectRefButton.Clicked = on_select_ref_image

def on_rand_seed_toggled(ev):
    # 勾选随机 ⇒ 禁用 SeedInput；未勾选 ⇒ 允许手动输入
    checked = runway_items["RandSeedCheckBox"].Checked
    runway_items["SeedInput"].Enabled = (not checked)

v2v_win.On.RandSeedCheckBox.Clicked = on_rand_seed_toggled


def switch_language(lang):
    if "MyTabs" in runway_items:
        for index, new_name in enumerate(translations[lang]["Tabs"]):
            runway_items["MyTabs"].SetTabText(index, new_name)

    for item_id, text_value in translations[lang].items():
        if item_id == "Tabs":
            continue
        if item_id in runway_items:
            runway_items[item_id].Text = text_value
        elif item_id in runway_config_items:    
            runway_config_items[item_id].Text = text_value
        else:
            print(f"[Warning] No control with ID {item_id} exists in runway_items, so the text cannot be set!")

def on_lang_checkbox_clicked(ev):
    is_en_checked = ev['sender'].ID == "LangEnCheckBox"
    runway_items["LangCnCheckBox"].Checked = not is_en_checked
    runway_items["LangEnCheckBox"].Checked = is_en_checked
    switch_language("en" if is_en_checked else "cn")
v2v_win.On.LangCnCheckBox.Clicked = on_lang_checkbox_clicked
v2v_win.On.LangEnCheckBox.Clicked = on_lang_checkbox_clicked

saved_settings = load_settings(SETTINGS)

if saved_settings:
    runway_items["Path"].Text = saved_settings.get("PATH", DEFAULT_SETTINGS["PATH"])
    runway_items["ModelCombo"].CurrentIndex = saved_settings.get("MODEL", DEFAULT_SETTINGS["MODEL"])
    runway_items["RatioCombo"].CurrentIndex = saved_settings.get("RATIO", DEFAULT_SETTINGS["RATIO"])
    runway_items["SeedInput"].Text = saved_settings.get("SEED", DEFAULT_SETTINGS["SEED"])
    runway_items["RandSeedCheckBox"].Checked = saved_settings.get("SEED_RANDOM", DEFAULT_SETTINGS["SEED_RANDOM"])
    runway_items["LangCnCheckBox"].Checked = saved_settings.get("CN", DEFAULT_SETTINGS["CN"])
    runway_items["LangEnCheckBox"].Checked = saved_settings.get("EN", DEFAULT_SETTINGS["EN"])
    runway_config_items["RunwayBaseURL"].Text = saved_settings.get("RUNWAY_BASE_URL", DEFAULT_SETTINGS["RUNWAY_BASE_URL"])
    runway_config_items["RunwayApiKey"].Text = saved_settings.get("RUNWAY_API_KEY", DEFAULT_SETTINGS["RUNWAY_API_KEY"])

    runway_items["SeedInput"].Enabled = (not runway_items["RandSeedCheckBox"].Checked)
    
if runway_items["LangEnCheckBox"].Checked :
    print("en")
    switch_language("en")
else:
    print("cn")
    switch_language("cn")

def on_post_clicked(ev):
    # 1) 基本就绪检查
    resolve, proj, mpool, root, tl, fps = connect_resolve()
    if not tl:
        show_dynamic_message("No active timeline.", "没有激活的时间线。")
        return

    # 2) 确保临时目录存在
    try:
        os.makedirs(TEMP_DIR, exist_ok=True)
    except Exception as e:
        show_dynamic_message(f"[Runway] Failed to prepare temp dir: {e}",
                             f"[Runway] 创建临时目录失败：{e}")
        return

    # 3) 渲染或复用缓存
    render_file = os.path.join(TEMP_DIR, f"render_{tl.GetUniqueId()}.mp4")
    if not os.path.exists(render_file):
        show_dynamic_message("[Runway] Rendering...", "[Runway] 视频处理中...")
        ratio = runway_items["RatioCombo"].CurrentText or "1280:720"
        render_file = render_video_by_marker(TEMP_DIR, f"render_{tl.GetUniqueId()}", ratio)
        if not render_file or not os.path.exists(render_file):
            show_dynamic_message("[Runway] Render failed.", "[Runway] 渲染失败。")
            return
    else:
        print(f"Found cached video: {render_file}. Skipping render.")

    # 4) Provider 参数校验与准备
    base_url = (runway_config_items["RunwayBaseURL"].Text or "").strip()
    api_key  = (runway_config_items["RunwayApiKey"].Text or "").strip()

    # Base URL 为空则采用默认
    if not base_url:
        base_url = RunwayProvider.BASE_URL

    if not api_key:
        show_dynamic_message("[Runway] Missing API Key.", "[Runway] 缺少 API Key。")
        return

    provider = RunwayProvider(base_url, api_key)

    # 5) 生成/读取种子，确保为 int
    import random, mimetypes
    use_random = runway_items["RandSeedCheckBox"].Checked
    seed = None
    if use_random:
        seed = random.randint(0, 4294967295)
        runway_items["SeedInput"].Text = str(seed)   # 回显
    else:
        seed_text = (runway_items["SeedInput"].Text or "").strip()
        seed = int(seed_text) if seed_text else None   # 为空则不传 seed
    ref_path = (runway_items["RefPath"].Text or "").strip()
    references = None
    if ref_path and os.path.exists(ref_path):
        try:
            img_uri = RunwayProvider._file_to_data_uri(ref_path)
            # tag 可用于在 prompt 中 @ref1 引用（图像端点明确支持；视频端点同结构）
            references = [{"type": "image", "uri": img_uri}]
        except Exception as e:
            print(f"[Runway] 参考图读入失败: {e}")
            references = None
            
    # 6) 发起任务
    show_dynamic_message("[Runway] Generating...", "[Runway] 生成中...")
    task_id = provider.video_to_video(
        video_path=render_file,
        prompt=runway_items["Prompt"].PlainText,
        model=runway_items["ModelCombo"].CurrentText or "gen4_aleph",
        ratio=runway_items["RatioCombo"].CurrentText or "1280:720",
        seed=seed,
        references=references
    )

    show_dynamic_message(f"[Runway] Task ID: {task_id}",
                         f"[Runway] 任务 ID: {task_id}")
    print(f"任务 ID: {task_id}")

    if not task_id:
        # video_to_video 已经做了详细报错提示
        return

    runway_items["TaskID"].Text = task_id

    # 7) 轮询拿结果 URL
    file_url = provider.get_task_status(task_id)
    if isinstance(file_url, list):  # 兼容列表返回
        file_url = file_url[0]

    if not file_url:
        show_dynamic_message("[Runway] No output URL.", "[Runway] 未获取到输出地址。")
        return

    # 8) 准备保存路径并下载
    save_path = generate_filename(
        runway_items["Path"].Text,
        runway_items["Prompt"].PlainText,
        ".mp4"
    )

    if not provider.download_file(file_url, save_path):
        show_dynamic_message("[Runway] Download Failed!", "[Runway] 下载失败！")
        return

    # 9) 写回时间线（基于第一个 marker 放置）
    timeline_start_frame = tl.GetStartFrame()
    markers = tl.GetMarkers()
    if not markers:
        show_dynamic_message("[Runway] No markers.", "[Runway] 未找到标记。")
        return

    first_frame_id = sorted(markers.keys())[0]
    local_start = int(first_frame_id)
    mark_in = timeline_start_frame + local_start

    success = add_to_media_pool_and_timeline(mark_in, tl.GetEndFrame(), save_path)
    if success:
        show_dynamic_message("[Runway] Finish!", "[Runway] 完成！")
        runway_items["TaskID"].Text = ""  # 成功后清空 TaskID
    else:
        show_dynamic_message("[Runway] Append to timeline failed.",
                             "[Runway] 添加到时间线失败。")

        

    
v2v_win.On.PostButton.Clicked = on_post_clicked

def on_get_clicked(ev):
    resolve, proj, mpool, root, tl, fps = connect_resolve()
    if not tl:
        show_dynamic_message("No active timeline.", "没有激活的时间线。")
        return
    base_url= runway_config_items["RunwayBaseURL"].Text
    api_key = runway_config_items["RunwayApiKey"].Text.strip()
    task_id = runway_items["TaskID"].Text.strip()
    if not task_id:
        show_dynamic_message("[Runway] Missing Task ID", "[Runway] 缺少任务 ID")
        return
    provider = RunwayProvider(base_url,api_key)

    show_dynamic_message("[Runway] Start...", "[Runway] 开始...") 
    file_url = provider.get_task_status(task_id)
    if isinstance(file_url, list):  # 兼容列表返回
        file_url = file_url[0]

    if not file_url:
        show_dynamic_message("[Runway] No output URL.", "[Runway] 未获取到输出地址。")
        return

    # 8) 准备保存路径并下载
    save_path = generate_filename(
        runway_items["Path"].Text,
        runway_items["Prompt"].PlainText,
        ".mp4"
    )

    if not provider.download_file(file_url, save_path):
        show_dynamic_message("[Runway] Download Failed!", "[Runway] 下载失败！")
        return

    # 9) 写回时间线（基于第一个 marker 放置）
    timeline_start_frame = tl.GetStartFrame()
    markers = tl.GetMarkers()
    if not markers:
        show_dynamic_message("[Runway] No markers.", "[Runway] 未找到标记。")
        return

    first_frame_id = sorted(markers.keys())[0]
    local_start = int(first_frame_id)
    mark_in = timeline_start_frame + local_start

    success = add_to_media_pool_and_timeline(mark_in, tl.GetEndFrame(), save_path)
    if success:
        show_dynamic_message("[Runway] Finish!", "[Runway] 完成！")
        runway_items["TaskID"].Text = ""  # 成功后清空 TaskID
    else:
        show_dynamic_message("[Runway] Append to timeline failed.",
                             "[Runway] 添加到时间线失败。")
v2v_win.On.GetButton.Clicked = on_get_clicked

def save_file():
    settings = {
        "RUNWAY_BASE_URL": runway_config_items["RunwayBaseURL"].Text,
        "RUNWAY_API_KEY": runway_config_items["RunwayApiKey"].Text,
        "PATH":runway_items["Path"].Text,
        "SEED": runway_items["SeedInput"].Text,
        "SEED_RANDOM": runway_items["RandSeedCheckBox"].Checked,
        "RATIO": runway_items["RatioCombo"].CurrentIndex,
        "MODEL": runway_items["ModelCombo"].CurrentIndex,
        "CN":runway_items["LangCnCheckBox"].Checked,
        "EN":runway_items["LangEnCheckBox"].Checked,
    }
    
    settings_file = os.path.join(SCRIPT_PATH, "config", "settings.json")
    try:
        os.makedirs(os.path.dirname(settings_file), exist_ok=True)
        
        with open(settings_file, 'w', encoding='utf-8') as f:
            json.dump(settings, f, ensure_ascii=False, indent=4)
        print(f"Settings saved to {settings_file}")
    except OSError as e:
        print(f"Error saving settings to {settings_file}: {e.strerror}")

def on_browse_button_clicked(ev):
    resolve, proj, mpool, root, tl, fps = connect_resolve()
    current_path = runway_items["Path"].Text
    selected_path = fusion.RequestDir(current_path)
    if selected_path:
        # 创建以项目名称命名的子目录
        project_subdir = os.path.join(selected_path, f"{proj.GetName()}_V2V")
        try:
            os.makedirs(project_subdir, exist_ok=True)
            runway_items["Path"].Text = str(project_subdir)
            print(f"Directory created: {project_subdir}")
        except Exception as e:
            print(f"Failed to create directory: {e}")
    else:
        print("No directory selected or the request failed.")
v2v_win.On.Browse.Clicked = on_browse_button_clicked

def on_text_changed(ev):
    if runway_items["TaskID"].Text:
        runway_items["GetButton"].Enabled = True
    else:
        runway_items["GetButton"].Enabled = False
v2v_win.On.TaskID.TextChanged = on_text_changed

def on_my_tabs_current_changed(ev):
    runway_items["MyStack"].CurrentIndex = ev["Index"]
v2v_win.On.MyTabs.CurrentChanged = on_my_tabs_current_changed

def on_open_link_button_clicked(ev):
    if runway_items["LangEnCheckBox"].Checked :
        webbrowser.open(SCRIPT_KOFI_URL)
    else :
        webbrowser.open(SCRIPT_BILIBILI_URL)
v2v_win.On.CopyrightButton.Clicked = on_open_link_button_clicked

def on_open_register_button_clicked(ev):
    webbrowser.open(RUNWAY_REGISTER_URL)
runway_config_win.On.RunwayRegisterButton.Clicked = on_open_register_button_clicked

def on_show_runway(ev):
    runway_config_win.Show()
v2v_win.On.ShowRunway.Clicked = on_show_runway

def on_runway_close(ev):
    print("API setup is complete.")
    runway_config_win.Hide()
runway_config_win.On.RunwayConfirm.Clicked = on_runway_close
runway_config_win.On.RunwayConfigWin.Close = on_runway_close

def on_close(ev):
    resolve, proj, mpool, root, tl, fps = connect_resolve()
    markers = tl.GetMarkers() or {}
    for frame_id, info in markers.items():
        if info.get("customData") == "v2v":
            tl.DeleteMarkerAtFrame(frame_id)

    for temp_dir in [TEMP_DIR]:
        if os.path.exists(temp_dir):
            try:
                import shutil
                shutil.rmtree(temp_dir)
                print(f"Removed temporary directory: {temp_dir}")
            except OSError as e:
                print(f"Error removing directory {temp_dir}: {e.strerror}")
    save_file()
    dispatcher.ExitLoop()
v2v_win.On.RunwayWin.Close = on_close

loading_win.Hide() 
runway_config_win.Hide() 
v2v_win.Show()
dispatcher.RunLoop()
v2v_win.Hide()