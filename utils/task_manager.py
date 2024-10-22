import math
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed


class ThreadPool:
    def __init__(self, max_workers=5):
        # 记录所有的子线程完成后的返回值
        self.results = []
        # 子线程函数体
        self.func = None
        # 需要传进子线程的参数，数组中每一个元素都是一个元组
        # 例如有一个函数定义 add(a, b)，参数数组表现为 [(1, 2), (3, 10), ...]
        self.args_list = None
        # 需要完成的任务的数量
        self.task_num = 0
        # 线程池同时容纳的最大线程数，默认为5
        self.max_workers = max_workers
        # 初始化线程池
        self.pool = ThreadPoolExecutor(max_workers=max_workers)

    # 设置线程池中执行任务的各项参数
    def submit_task(self, func, args_list):
        # 设置任务数和任务参数
        self.task_num = len(args_list)
        self.args_list = args_list
        self.func = func

    # 显示进度条，用以查看所有任务的完成进度
    @staticmethod
    def show_process(desc_text, curr, total):
        proc = math.ceil(curr / total * 100)
        show_line = '\r' + desc_text + ':' + '>' * proc \
                    + ' ' * (100 - proc) + '[%s%%]' % proc \
                    + '[%s/%s]' % (curr, total)
        sys.stdout.write(show_line)
        sys.stdout.flush()

    # 获取最终所有线程完成后的处理结果
    def final_results(self):
        # 使用 futures 提交所有任务
        futures = [self.pool.submit(self.func, *args) for args in self.args_list]

        # 监控每个任务的完成状态
        for future in as_completed(futures):
            try:
                result = future.result()  # 获取每个任务的返回结果
                self.results.append(result)
                # 显示进度
                self.show_process('任务完成进度', len(self.results), self.task_num)
            except Exception as e:
                print(f"\n任务执行出错：{e}")

        # 所有任务完成后返回结果
        return self.results


