import cv2
import numpy as np
from sklearn.cluster import KMeans
from collections import defaultdict
import matplotlib.pyplot as plt
import tkinter as tk
from PIL import ImageGrab, ImageTk
import ctypes

IMAGE_PATH = "grid3.png"


# -------------------------------------------------
# 1 识别网格大小
# -------------------------------------------------
def detect_grid(img):

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    edges = cv2.Canny(gray, 50, 150)

    lines = cv2.HoughLinesP(edges, 1, np.pi/180, 50,
                            minLineLength=30,
                            maxLineGap=20)

    vertical = []
    horizontal = []

    if lines is not None:
        for x1,y1,x2,y2 in lines[:,0]:

            if abs(x1-x2) < 10:
                vertical.append(x1)

            if abs(y1-y2) < 10:
                horizontal.append(y1)

    vertical = sorted(vertical)
    horizontal = sorted(horizontal)

    # 去重
    def unique(vals, thresh=20):
        res = []
        for v in vals:
            if not res or abs(v-res[-1]) > thresh:
                res.append(v)
        return res

    vertical = unique(vertical)
    horizontal = unique(horizontal)

    cols = len(vertical)-1
    rows = len(horizontal)-1

    return rows, cols, vertical, horizontal


# -------------------------------------------------
# 2 切分格子
# -------------------------------------------------
def extract_cells(img, rows, cols, vertical, horizontal):

    cells = []

    for r in range(rows):
        row = []

        for c in range(cols):

            x1 = vertical[c]
            x2 = vertical[c+1]

            y1 = horizontal[r]
            y2 = horizontal[r+1]

            cell = img[y1:y2, x1:x2]

            row.append(cell)

        cells.append(row)

    return cells


# -------------------------------------------------
# 3 获取格子主颜色
# -------------------------------------------------
def cell_color(cell):

    h,w,_ = cell.shape

    center = cell[h//4:3*h//4, w//4:3*w//4]

    avg = center.reshape(-1,3).mean(axis=0)

    return avg


# -------------------------------------------------
# 4 聚类颜色
# -------------------------------------------------
def cluster_colors(cells):

    rows = len(cells)
    cols = len(cells[0])

    colors = []

    for r in range(rows):
        for c in range(cols):
            colors.append(cell_color(cells[r][c]))

    colors = np.array(colors)

    # 颜色数量等于行数
    n_clusters = rows

    try:
        # 尝试使用KMeans聚类
        kmeans = KMeans(n_clusters=n_clusters, n_init=10, random_state=42)
        labels = kmeans.fit_predict(colors)
    except Exception as e:
        print(f"聚类失败: {e}")
        # 使用基于行的颜色分类作为替代方案
        labels = np.zeros(len(colors), dtype=int)
        # 为每行分配不同的颜色类别
        for r in range(rows):
            for c in range(cols):
                # 基于行索引分配类别
                labels[r * cols + c] = r % n_clusters

    grid = labels.reshape(rows,cols)

    return grid


# -------------------------------------------------
# 5 检查相邻
# -------------------------------------------------
def adjacent(a,b):

    r1,c1 = a
    r2,c2 = b

    return abs(r1-r2)<=1 and abs(c1-c2)<=1


# -------------------------------------------------
# 6 求解炸弹
# -------------------------------------------------
def solve(grid):

    rows,cols = grid.shape

    color_cells = defaultdict(list)

    for r in range(rows):
        for c in range(cols):
            color_cells[grid[r][c]].append((r,c))

    colors = list(color_cells.keys())

    result = []

    used_rows=set()
    used_cols=set()

    def dfs(i):

        if i == len(colors):
            return True

        color = colors[i]

        for r,c in color_cells[color]:

            if r in used_rows:
                continue

            if c in used_cols:
                continue

            ok=True

            for br,bc in result:
                if adjacent((r,c),(br,bc)):
                    ok=False
                    break

            if not ok:
                continue

            result.append((r,c))
            used_rows.add(r)
            used_cols.add(c)

            if dfs(i+1):
                return True

            result.pop()
            used_rows.remove(r)
            used_cols.remove(c)

        return False

    dfs(0)

    return result


# -------------------------------------------------
# 7 标记炸弹
# -------------------------------------------------
def draw_bombs(img, bombs, rows, cols):

    h,w = img.shape[:2]

    cell_h = h/rows
    cell_w = w/cols

    for r,c in bombs:

        x = int((c+0.5)*cell_w)
        y = int((r+0.5)*cell_h)

        cv2.circle(img,(x,y),20,(0,0,255),4)

    return img


# -------------------------------------------------
# 主程序
# -------------------------------------------------
def process_image(img):
    """处理图像并返回结果和炸弹坐标"""
    rows,cols,vertical,horizontal = detect_grid(img)
    
    print("网格:",rows,"x",cols)
    
    if rows <= 0 or cols <= 0:
        print("无法检测到有效的网格")
        return None, None
    
    cells = extract_cells(img,rows,cols,vertical,horizontal)
    
    grid = cluster_colors(cells)
    
    print("颜色矩阵:")
    print(grid)
    
    bombs = solve(grid)
    bombscood=[(j+1,rows-i) for i,j in bombs]
    
    print("炸弹:",bombscood)
    
    result = draw_bombs(img,bombs,rows,cols)
    
    cv2.imwrite("result.png",result)
    return result, bombscood

def main():

    # --------- DPI 修复（必须在Tk之前）---------
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except:
        pass

    root = tk.Tk()
    root.title("找牛牛 - 炸弹检测")

    root.geometry("800x600")
    root.attributes("-topmost", True)

    root.wm_attributes('-transparentcolor', 'red')

    # 主框架
    main_frame = tk.Frame(root)
    main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

    # 透明截图区域
    transparent_frame = tk.Frame(main_frame, bg='red')
    transparent_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

    # 按钮区
    button_frame = tk.Frame(main_frame)
    button_frame.pack(fill=tk.X, padx=10, pady=10)

    # 炸弹坐标显示区
    bomb_frame = tk.Frame(main_frame)
    bomb_frame.pack(fill=tk.X, padx=10, pady=10)

    # 炸弹坐标标签
    bomb_label = tk.Label(bomb_frame, text="炸弹坐标XY:", font=('Arial', 12))
    bomb_label.pack(side=tk.LEFT, padx=5)

    # 炸弹坐标文本框
    bomb_text = tk.Text(bomb_frame, height=1, font=('Arial', 12), state=tk.DISABLED)
    bomb_text.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)

        # 炸弹坐标显示区
    bomb_frame2 = tk.Frame(main_frame)
    bomb_frame2.pack(fill=tk.X, padx=10, pady=10)

        # 炸弹坐标标签
    bomb_label2 = tk.Label(bomb_frame2, text="炸弹坐标YX:", font=('Arial', 12))
    bomb_label2.pack(side=tk.LEFT, padx=5)

    # 炸弹坐标文本框
    bomb_text2 = tk.Text(bomb_frame2, height=1, font=('Arial', 12), state=tk.DISABLED)
    bomb_text2.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)

    # -------------------------------
    # 截图函数
    # -------------------------------
    def capture_and_process():

        root.update()

        # 获取截图区域
        x = transparent_frame.winfo_rootx()
        y = transparent_frame.winfo_rooty()
        w = transparent_frame.winfo_width()
        h = transparent_frame.winfo_height()

        print("截图区域:", x, y, w, h)

        # 临时隐藏窗口（避免截进去）
        root.withdraw()
        root.update()

        try:
            screenshot = ImageGrab.grab(bbox=(x, y, x+w, y+h))

        finally:
            root.deiconify()
            root.attributes("-topmost", True)

        # 转opencv
        img = np.array(screenshot)
        img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)

        # 处理图像
        result, bombscood = process_image(img)

        if result is not None:
            # 更新炸弹坐标文本框
            bomb_text.config(state=tk.NORMAL)
            bomb_text.delete(1.0, tk.END)
            bomb_text.insert(tk.END, ' '.join(f'{x}-{y}' for x, y in bombscood))
            bomb_text.config(state=tk.DISABLED)

            bomb_text2.config(state=tk.NORMAL)
            bomb_text2.delete(1.0, tk.END)
            bomb_text2.insert(tk.END, ' '.join(f'{y}-{x}' for x, y in bombscood))
            bomb_text2.config(state=tk.DISABLED)

            plt.figure(figsize=(10,6))

            img_rgb = cv2.cvtColor(result, cv2.COLOR_BGR2RGB)

            plt.imshow(img_rgb)
            plt.title("Result")
            plt.axis("off")

            plt.show()


    capture_button = tk.Button(
        button_frame,
        text="截图并找炸弹",
        command=capture_and_process,
        font=('Arial',12),
        height=2
    )

    capture_button.pack(fill=tk.X)

    root.mainloop()


if __name__ == "__main__":
    main()