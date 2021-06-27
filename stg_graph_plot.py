import sys
import os
import tkinter as tk
from tkinter import filedialog
from tkinter import messagebox
import tkinter.ttk as ttk
import pandas as pd
import time
import re
import matplotlib
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.ticker import ScalarFormatter

plt.style.use('ggplot')
font = {'family' : 'meiryo'}
matplotlib.rc('font', **font)

# 集計単位の選択肢
mean_times = {
    "生データ"   : "org",
    "30秒平均"   : "30S",
    "1分平均"    : "1T",
    "2分平均"    : "2T",
    "5分平均"    : "5T",
    "10分平均"   : "10T",
    "15分平均"   : "15T",
    "30分平均"   : "30T",
    "1時間平均"  : "1H",
    "3時間平均"  : "3H",
    "6時間平均"  : "6H",
    "12時間平均" : "12H",
    "1日平均"    : "1D",
}

# LabelFrameの共通オプション
lf_opt = {
    "padx" : 4,
    "labelanchor" : tk.NW,
    "foreground" : "blue",
}

# Comboboxの共通オプション
cb_opt = {
    "width" : 12,
}

#=================================================================
class SelectMeanTimeFrame(tk.LabelFrame):
    '''集計単位の選択フレーム'''
    def __init__(self, var_mean_time, master=None, *args, **kwdargs):
        self.var_mean_time = var_mean_time
        super().__init__(master, text="集計単位", *args, **kwdargs)
        cb = ttk.Combobox(
            master=self,
            values=list(mean_times.keys()),
            textvariable=self.var_mean_time,
            state="readonly",
            **cb_opt,
        )
        cb.current(4)         # 初期値を設定
        cb.grid(row=3, column=0)
        #cb.bind("<<ComboboxSelected>>", self.print_var)
        #self.print_var()

    def print_var(self, event=None):
        print("集計時間", self.var_mean_time.get(), mean_times[self.var_mean_time.get()])

#=================================================================
class SelectOutputPeriodFrame(tk.LabelFrame,):
    '''対象期間の選択フレーム'''
    def __init__(self, dates, var_from, var_to, master=None, *args, **kwdargs):
        self.var_from = var_from
        self.var_to   = var_to
        super().__init__(master, text="対象期間", *args, **kwdargs)

        # 開始日
        self.cb_from = ttk.Combobox(
            master=self,
            values=[str(d) for d in dates],
            textvariable=self.var_from,
            state="readonly",
            **cb_opt,
        )
        self.cb_from.current(0) # 初期値を設定
        self.cb_from.grid(row=0, column=0)

        tk.Label(master=self, text="～").grid(row=0,column=1)

        # 終了日
        self.cb_to = ttk.Combobox(
            master=self,
            values=[str(d) for d in dates],
            textvariable=self.var_to,
            state="readonly",
            **cb_opt,
        )
        self.cb_to.current(len(dates)-1) # 初期値を設定
        self.cb_to.grid(row=0, column=2)

        self.cb_from.bind("<<ComboboxSelected>>", self.check_var_to)
        self.cb_from.bind("<MouseWheel>", self.check_var_to)
        self.cb_to.bind("<<ComboboxSelected>>", self.check_var_from)
        self.cb_to.bind("<MouseWheel>", self.check_var_from)

    # from の日付が to を超えたら to の値を修正する
    def check_var_to(self, event=None):
        if self.var_from.get() > self.var_to.get():
            #messagebox.showwarning('期間指定の補正', "終了日を変更しました")
            self.var_to.set(self.var_from.get())
        print(self.var_from.get(), "～", self.var_to.get())

    # to の日付が from を下回ったら from の値を修正する
    def check_var_from(self, event=None):
        if self.var_from.get() > self.var_to.get():
            #messagebox.showwarning('期間指定の補正', "開始日を変更しました")
            self.var_from.set(self.var_to.get())
        print(self.var_from.get(), "～", self.var_to.get())

#=================================================================
class SelectAxisScaleFrame(tk.LabelFrame):
    '''縦軸のスケールを指定するフレーム'''
    def __init__(self, var_unit, var_type, var_value, master=None, *args, **kwdargs):
        self.var_axis_unit  = var_unit
        self.var_axis_type  = var_type
        self.var_axis_value = var_value
        # 縦軸のスケールの辞書
        self.axis_values = {}
        self.axis_values.update({"{} Mbps".format(i) : int(i*1e6) for i in range(  1,  10,  1)})
        self.axis_values.update({"{} Mbps".format(i) : int(i*1e6) for i in range( 10, 100, 10)})
        self.axis_values.update({"{} Mbps".format(i) : int(i*1e6) for i in range(100,1000,100)})
        self.axis_values.update({"{} Gbps".format(i) : int(i*1e9) for i in range(  1,  11,  1)})
        # 縦軸の単位とspinboxの増分の辞書
        self.axis_units = { 
            "bps"  : int(  1e3),
            "kbps" : int(100e3),
            "Mbps" : int(  1e6),
            "Gbps" : int(  1e6),
        }

        super().__init__(master, text="縦軸の設定", *args, **kwdargs)

        # 子フレーム：単位
        lf = tk.LabelFrame(self, text="単位", **lf_opt)
        lf.pack(anchor=tk.W, fill=tk.X)
        for text in self.axis_units.keys():
            tk.Radiobutton(
                master=lf,
                text=text,
                value=text,
                variable=self.var_axis_unit,
                command=self.set_increment
            ).pack(anchor=tk.W, side=tk.LEFT)

        # 子フレーム：スケール
        lf = tk.LabelFrame(self, text="スケール", **lf_opt)
        lf.pack(anchor=tk.W, fill=tk.X)

        # 1列目、自動 or 固定 or 指定のラジオボタン
        for row, (text, value) in enumerate([["自動", "auto"], ["固定", "fix"], ["指定", "specified"]]):
            tk.Radiobutton(
                master=lf,
                text=text,
                variable=self.var_axis_type,
                value=value,
                command=self.change_state
            ).grid(row=row, column=0, sticky=tk.NW)

        # 1行/2列目、固定値の選択リスト
        self.cb = ttk.Combobox(
            master=lf,
            values=list(self.axis_values.keys()),
            state="disable",
            **cb_opt,
        )
        self.cb.current(9) # 初期値を指定
        self.cb.bind("<<ComboboxSelected>>", self.set_var_axis_value)
        self.cb.bind("<MouseWheel>", self.set_var_axis_value)

        self.cb.grid(row=1, column=1)

        # 2行/2列目、指定値の入力欄
        self.sb = tk.Spinbox(
            master=lf,
            textvariable = self.var_axis_value,
            from_ = 1,
            to = 10e9,
            increment = 1000,
            command = self.spin_changed,
            state = "disable",
            **cb_opt,
        )
        self.sb.grid(row=2, column=1, sticky=tk.W)
        self.set_var_axis_value() # 初期値に合わせて変数を設定
        self.sb.bind('<MouseWheel>', self.spin_wheel)
        tk.Label(lf,text="bps").grid(row=2, column=2)

    def spin_wheel(self, event):
        increment = int(self.sb.config("increment")[4])
        value = self.var_axis_value.get()
        if (event.delta > 0): # 上向きホイール
            value += increment
        elif (event.delta < 0): # 下向きホイール
            value -= increment
        if value <= 0: value = increment
        self.var_axis_value.set(value)

    def set_var_axis_value(self, event=None):
        self.var_axis_value.set(self.axis_values[self.cb.get()])
        #print("縦軸の値", self.var_axis_value.get())

    def spin_changed(self):
        try:
            self.var_axis_value.get()
        except:
            self.var_axis_value.set(1)
        if self.var_axis_value.get() < 1: #0より下の値を入力した時、1にする
            self.var_axis_value.set(1)

    # spinboxの増分を設定
    def set_increment(self):
        self.sb["increment"] = self.axis_units[self.var_axis_unit.get()]
        #print("増分", self.axis_units[self.var_axis_unit.get()])

    # に合わせて値の選択をactive or disableにする
    def change_state(self):
        if self.var_axis_type.get() == "fix":
            self.cb["state"] = "readonly"
            self.sb["state"] = "disable"
            self.set_var_axis_value()
        elif self.var_axis_type.get() == "specified":
            self.cb["state"] = "disable"
            self.sb["state"] = "normal"
        else:
            self.cb["state"] = "disable"
            self.sb["state"] = "disable"

#=================================================================
class ExecFrame(tk.Frame):
    def __init__(self, var_mean_time, var_axis_unit, var_from, var_to, csv_data, target_ip="unknown-host", master=None, *args, **kwargs):
        self.var_mean_time = var_mean_time
        self.var_axis_unit = var_axis_unit
        self.var_from = var_from
        self.var_to   = var_to
        self.csv_data = csv_data
        self.target_ip = target_ip
        super().__init__(master=master)
        # 実行ボタン
        tk.Button(self, text="グラフ表示", width=len("グラフ表示")*2, command=self.output_graph).pack(side=tk.LEFT,padx=2, pady=2)
        # 終了ボタン
        tk.Button(self, text="終了", command=self.abort).pack(side=tk.LEFT, padx=2, pady=2)

    def abort(self):
        plt.close('all')
        root.destroy()

    def output_graph(self):
        '''
        指定の時間でスループットを計算してCSVに吐き出す
        グラフも表示する。
        '''
        rule = mean_times[self.var_mean_time.get()]
        axis_unit = self.var_axis_unit.get()

        # 指定時間で集約
        if rule == "org":
            df = self.csv_data.copy()
        else:
            df = self.csv_data.resample(rule=rule).sum()

        # 指定期間を抽出
        df = df[self.var_from.get() : self.var_to.get()]

        # スループットを計算
        if axis_unit == "bps":
            div_unit = 1
        elif axis_unit == "kbps":
            div_unit = int(1e3)
        elif axis_unit == "Mbps":
            div_unit = int(1e6)
        elif axis_unit == "Gbps":
            div_unit = int(1e9)

        recv_unit = 'recv_' + axis_unit
        send_unit = 'send_' + axis_unit
        df[recv_unit] = df['recv'] * 8 * 100 // df['delta_time'] / div_unit
        df[send_unit] = df['send'] * 8 * 100 // df['delta_time'] / div_unit

        # CSVファイル出力
        output_columns = ["delta_time", recv_unit, send_unit]
        df[output_columns].to_csv("{}_{}.csv".format(self.target_ip, var_mean_time.get()), sep=",")

        # 送受信の最大値と発生日時を調べる
        recv_max = df[recv_unit].max()
        send_max = df[send_unit].max()
        recv_max_date = re.sub(r"\.\d+$", "", str(df[df[recv_unit] == recv_max].index.tolist()[0]))
        send_max_date = re.sub(r"\.\d+$", "", str(df[df[send_unit] == send_max].index.tolist()[0]))

        # 送受信の最大値の文字列を作成、MbpsとGbpsは少数点3桁表示
        if axis_unit == "Mbps" or axis_unit == "Gbps":
            recv_max_str = "{:,.3f}".format(recv_max)
            send_max_str = "{:,.3f}".format(send_max)
        else:
            recv_max_str = "{:,}".format(int(recv_max))
            send_max_str = "{:,}".format(int(send_max))

        strlen_max = max(len(recv_max_str), len(send_max_str))

        str1 = "受信MAX: {max:>{len}} {unit} ({date})".format(
            max  = recv_max_str,
            date = recv_max_date,
            unit = axis_unit,
            len  = strlen_max,
        )
        str2 = "送信MAX: {max:>{len}} {unit} ({date})".format(
            max  = send_max_str,
            date = send_max_date,
            unit = axis_unit,
            len  = strlen_max,
        )

        # グラフ描画
        ax = df.plot(
            grid=True,
            y=[recv_unit, send_unit],
            title='{} スループット（{}）'.format(self.target_ip, var_mean_time.get())
            )
        # X軸ラベル
        ax.set_xlabel("日時")
        # Y軸ラベル
        ax.set_ylabel(axis_unit)
        ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, loc: "{:,}".format(int(x))))
        ax.grid(which='major',color='gray',linestyle='--')
        ax.grid(which='minor',color='gray',linestyle='--')
         # Y軸のスケール
        if var_axis_type.get() == "auto":
            ax.set_ylim(0,)
        else:
            ax.set_ylim([0, var_axis_value.get() // div_unit])

        # 送受信の最大値をグラフ上にテキスト表示
        ax.text(0.05, 0.9, str1 + "\n" + str2, family='ms gothic', transform=ax.transAxes)

        plt.show()

#=================================================================
class ExecTime():
    '''コマンドの実行時間を測定する'''
    def __init__(self, init_time=0):
        self.t1 = time.time() if init_time == 0 else init_time
    @property
    def laptime(self):
        t2 = time.time()
        result = t2 - self.t1
        self.t1 = t2
        return result
    @property
    def print(self):
        print("{:.3f} sec".format(self.laptime))

#=================================================================
# メインルーチン
#=================================================================
if __name__ == "__main__":
    root = tk.Tk()
    root.withdraw()

    # CSVファイルの指定
    # コマンドライン引数で指定
    if len(sys.argv) > 1: 
        csv_filenames = sys.argv[1:] 
    # filedialogで選択
    else:
        filetypes = [("STGローテーションファイル", "*.csv*"), ("CSV", "*.csv"), ("すべて", "*"), ]
        csv_filenames = filedialog.askopenfilenames(filetypes=filetypes) # キャンセル時は''
        # ファイル指定がなければ終了
        if csv_filenames == '':
            root.destroy()

    # CSVファイルのチェック
    # 1.STGのファイルであること
    # 2.同じホストの同じインタフェースのデータであること
    # を各ファイルの1行目の文字列で調べる
    target = None
    for filename in csv_filenames:
        line = ""
        try:
            with open(filename, "r", encoding="utf-8") as f:
                line = f.readline().rstrip() # 1行読み込み
        except UnicodeDecodeError as err:
            messagebox.showerror('文字コードエラー', '文字コードがUTF-8ではありません\n{}\n{}'.format(filename, err))
            exit()
        except Exception as other:
            messagebox.showerror('ファイルオープンエラー', 'ファイルが開けません\n{}\n{}'.format(filename, other))
            exit()

        # STGのファイルであることのチェック
        # 行頭がSTGでカンマ区切りで5カラムあること
        columns = re.split(",", line)
        if len(line) < 3 or line[:3] != "STG" or len(columns) != 5:
            messagebox.showerror(
                'ファイルフォーマットエラー',
                'STGのCSVファイルではありません\n{}'.format(filename)
            )
            exit()
        else:
            m = re.match("Target Address:(.+)", columns[1])
            if not m:
                messagebox.showerror(
                    'ファイルフォーマットエラー',
                    'STGのCSVファイルではありません\n{}'.format(filename)
                )
                exit()
            else:
                target_ip = m.group(1)

        # 4カラムをターゲット情報として保存
        if target == None:
            target = columns[1:]

        # 対象情報がすべてのファイルで一致するか
        elif target != columns[1:]: 
            print("{} の対象情報が一致しません".format(os.path.basename(filename)))
            for s in columns[1:]:
                print("  ", s)
            exit()

    # CSVファイルの読込
    t = ExecTime()
    for idx, filename in enumerate(csv_filenames):
        print(
            "ファイル読込 ({}/{})：{} ... ".format(idx+1, len(csv_filenames), filename),
            end="",
            file=sys.stderr,
            flush=True,
        )
        df = pd.read_csv(
            filename,
            encoding='SHIFT-JIS',                       # 文字コードを指定
            header=1,                                   # 0行目（最初の行）を読み飛ばす
            names=['date', 'uptime', 'recv', 'send'],   # カラム名を設定
            parse_dates=['date'],                       # datetime で読み込むカラムを指定
            index_col=['date'],                         # インデックスを指定
            )
        if idx == 0: # ファイル1個目
            csv_data = df
        else:        # ファイル2個目以降
            csv_data = pd.concat([csv_data, df])
        t.print # ファイル読み込み時間表示

    csv_data.drop_duplicates(inplace=True)              # 重複行を削除する
    csv_data = csv_data.sort_index()                    # インデックス順（日時）でソートする
    csv_data = csv_data.query('uptime != 0')            # uptimeが0の行を削除する #別の書き方 df = df[df['uptime'] != 0]
    csv_data['delta_time'] = csv_data['uptime'].diff()  # delta_timeを計算する。
    csv_data.drop('uptime', axis=1, inplace=True)       # uptimeを削除する

    # tkinterのウィジェット設定
    # 機器情報
    lf = tk.LabelFrame(text="機器情報", **lf_opt)
    [tk.Label(lf, text=target[i], anchor=tk.W).pack(fill=tk.X) for i in [0,2,3]]
    lf.pack(fill=tk.X)

    # ファイル情報
    lf = tk.LabelFrame(text="CSV情報", **lf_opt)
    recv  = csv_data['recv'] * 8 * 100 // csv_data['delta_time']
    send  = csv_data['send'] * 8 * 100 // csv_data['delta_time']
    delta = csv_data['delta_time'] / 100
    text = [
        "開始日時: {}".format(str(csv_data.index[ 0])[:-7]),
        "終了日時: {}".format(str(csv_data.index[-1])[:-7]),
        "取得間隔: {:,} ～ {:,} 秒".format(delta.min(), delta.max()),
        "取得行数: {:,}".format(csv_data.shape[0]),
        "受信帯域: 最大 {:,} bps".format(int(recv.max())),
        "送信帯域: 最大 {:,} bps".format(int(send.max())),
    ]
    [tk.Label(lf, text=s, anchor=tk.W).pack(fill=tk.X) for s in text]
    lf.pack(fill=tk.X)

    # ウィジェット共通の変数
    var_axis_unit  = tk.StringVar(value="kbps") # 縦軸の単位 bps / kbps / Mbps
    var_axis_type  = tk.StringVar(value="auto") # 縦軸の指定方法 auto / fix
    var_axis_value = tk.IntVar()                # 縦軸の高さ
    var_mean_time  = tk.StringVar()             # 集計時間
    var_from       = tk.StringVar()
    var_to         = tk.StringVar()

    # 集計単位の選択
    SelectMeanTimeFrame(
        var_mean_time,
        master=root,
        **lf_opt,
    ).pack(anchor=tk.W, fill=tk.X, ipady=2)

    # 期間指定
    SelectOutputPeriodFrame(
        sorted(set(csv_data.index.date)),
        var_from,
        var_to,
        **lf_opt,
    ).pack(anchor=tk.W, fill=tk.X, ipady=2)

    # 縦軸のスケールを選択
    SelectAxisScaleFrame(
        var_axis_unit,
        var_axis_type,
        var_axis_value,
        **lf_opt,
    ).pack(anchor=tk.W, fill=tk.X, ipady=2)

    # 実行ボタン
    ExecFrame(
        var_mean_time,
        var_axis_unit,
        var_from,
        var_to,
        csv_data,
        target_ip
    ).pack()

    root.title('STG集計ツール')
    root.resizable(width=False, height=False)
    root.deiconify()
    root.mainloop()
