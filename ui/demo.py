import whisper
import os
import gradio as gr
from moviepy.video.io.VideoFileClip import VideoFileClip

# 生成字幕文件
def generate_subtitles(video_path):
    model = whisper.load_model("base")
    result = model.transcribe(video_path)
    srt_path = video_path.replace('.mp4', '.srt')  # 在素材目录下生成 .srt 文件
    with open(srt_path, 'w', encoding='utf-8') as srt_file:
        for i, segment in enumerate(result['segments']):
            start = segment['start']
            end = segment['end']
            text = segment['text']
            srt_file.write(f"{i + 1}\n{start:.3f} --> {end:.3f}\n{text}\n\n")
    return srt_path

# 处理素材文件夹中的所有视频，生成.srt文件
def create_index(input_folder):
    video_files = [f for f in os.listdir(input_folder) if f.endswith('.mp4')]
    created_files = []

    for video in video_files:
        video_path = os.path.join(input_folder, video)
        srt_path = generate_subtitles(video_path)  # 在素材文件夹生成 .srt
        created_files.append({"video": video, "srt": srt_path})

    return created_files

# 搜索字幕中的关键字
def search_in_subtitles(input_folder, keyword):
    results = []
    video_files = []
    for file in os.listdir(input_folder):
        if file.endswith('.srt'):
            srt_path = os.path.join(input_folder, file)
            video_file = srt_path.replace('.srt', '.mp4')  # 获取同名视频文件
            with open(srt_path, 'r', encoding='utf-8') as f:
                content = f.read()
                lines = content.split('\n')
                for i, line in enumerate(lines):
                    if keyword.lower() in line.lower():
                        # 显示为 目录 + 视频名称 --- 符合的字幕内容
                        results.append(f"{video_file} --- {line}")
                        video_files.append(video_file)
    return results, list(set(video_files))  # 返回搜索结果和唯一的视频文件列表

# 视频剪辑
def clip_video(video_path, start_time, end_time, output_path):
    with VideoFileClip(video_path) as video:
        clip = video.subclip(start_time, end_time)
        clip.write_videofile(output_path, codec="libx264")
    return output_path

# Gradio 界面布局
def create_interface():
    with gr.Blocks() as app:
        with gr.Row():  # 文件夹选择
            input_folder = gr.Textbox(label="素材文件夹", value="/Users/zoukaixin/Downloads/sucai",placeholder="选择素材文件夹路径")
            output_folder = gr.Textbox(label="输出文件夹",value="/Users/zoukaixin/Downloads/ouputs", placeholder="选择输出文件夹路径")

        with gr.Row():  # 索引生成与关键字搜索
            create_index_btn = gr.Button("创建索引")
            search_keyword = gr.Textbox(label="输入关键字", placeholder="请输入搜索关键词")
            search_btn = gr.Button("搜索")

        # 搜索结果展示，结果显示可以被选择
        search_results = gr.Textbox(label="搜索结果", lines=10, interactive=True, placeholder="搜索结果将显示在这里")

        with gr.Row():  # 剪辑功能
            clip_start = gr.Number(label="剪辑开始时间 (秒)")
            clip_end = gr.Number(label="剪辑结束时间 (秒)")
            clip_btn = gr.Button("开始剪辑")

        log_display = gr.Textbox(label="日志记录", lines=10, placeholder="操作日志会显示在这里")

        # 创建索引按钮点击事件
        def on_create_index(input_folder):
            created_files = create_index(input_folder)
            log = "\n".join([f"生成字幕: {f['video']} -> {f['srt']}" for f in created_files])
            return log

        # 搜索字幕关键词事件
        def on_search(input_folder, keyword):
            results,video_list = search_in_subtitles(input_folder, keyword)
            return "\n".join(results)  # 将结果格式化为多行文本

        # 视频剪辑事件
        def on_clip_video(input_folder, output_folder, start_time, end_time):
            selected_file = search_results.value.strip().split(" --- ")[0]  # 获取被选择的视频文件路径
            if selected_file and selected_file.endswith('.srt'):
                video_file = selected_file.replace('.srt', '.mp4')
                output_path = os.path.join(output_folder, f"clip_{start_time}_{end_time}.mp4")
                clip_video(video_file, start_time, end_time, output_path)
                return f"剪辑完成: {output_path}"
            else:
                return "未选择有效的文件进行剪辑"

        # 绑定按钮事件
        create_index_btn.click(on_create_index, inputs=[input_folder], outputs=[log_display])
        search_btn.click(on_search, inputs=[input_folder, search_keyword], outputs=[search_results])
        clip_btn.click(on_clip_video, inputs=[input_folder, output_folder, clip_start, clip_end], outputs=[log_display])

    return app

# 启动 Gradio 应用
app = create_interface()
app.launch()