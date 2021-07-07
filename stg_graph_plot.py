import datetime
import os
import re
import threading
import time
import tkinter as tk
import tkinter.scrolledtext as tkst
import tkinter.ttk as ttk
from tkinter import filedialog, messagebox

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import pandas as pd
# from matplotlib.backend_bases import key_press_handler
from matplotlib.backends.backend_tkagg import (FigureCanvasTkAgg,
                                               NavigationToolbar2Tk)
from matplotlib.figure import Figure
from matplotlib.ticker import AutoMinorLocator

__version__ = '1.1.0'
plt.style.use('ggplot')
font = {'family': 'meiryo'}
plt.rc('font', **font)

# 集計単位の選択肢
MEAN_TIMES = {
    '生データ': 'org',
    '10秒平均': '10S',
    '15秒平均': '15S',
    '30秒平均': '30S',
    '1分平均': '1T',
    '2分平均': '2T',
    '5分平均': '5T',
    '10分平均': '10T',
    '15分平均': '15T',
    '30分平均': '30T',
    '1時間平均': '1H',
    '3時間平均': '3H',
    '6時間平均': '6H',
    '12時間平均': '12H',
    '1日平均': '1D',
}


def now(format: str = '%Y-%m-%d %H:%M:%S') -> str:
    """現在時刻文字列を返す
    """
    return datetime.datetime.now().strftime(format)


class MyLabelFrame(tk.LabelFrame):
    def __init__(self, master=None, **kwargs):
        super().__init__(
            master=master,
            padx=4,
            labelanchor=tk.NW,
            foreground='blue',
        )
        self.config(**kwargs)  # 指定オプションの設定

    def grid(self, **kwargs):
        super().grid(
            sticky=tk.NSEW,
            ipady=2,
            padx=2,
            pady=2,
            **kwargs,
        )


class MyCombobox(ttk.Combobox):
    """Combobox（リスト）
    """
    def __init__(self, master=None, **kwargs):
        super().__init__(
            master=master,
            width=12,
            state='readonly',
        )
        self.config(**kwargs)  # 指定オプションの設定


class MySpinbox(ttk.Spinbox):
    """Spinbox（増減ボタンありのEntry）
    """
    def __init__(self, master=None, **kwargs):
        super().__init__(
            master=master,
            width=12,
        )
        self.config(**kwargs)  # 指定オプションの設定


class MyScrolledText(tkst.ScrolledText):
    """スクロールするテキストウィジェット
    """
    def __init__(self, master=None, **kwargs):
        super().__init__(
            master=master,
            width=100,
            state=tk.DISABLED,
        )
        self.config(**kwargs)  # 指定オプションの設定

    def grid(self, **kwargs):
        super().grid(
            sticky=(tk.N, tk.S, tk.E, tk.W),
            ipady=2,
            padx=2,
            pady=2,
            **kwargs,
        )

    def write(self, text: str):
        """テキストメッセージの追記
            末尾に追記し、最終行にスクロールする

        Args:
            text (str): 追記するテキスト
        """
        self['state'] = tk.NORMAL
        self.insert('end', text)
        self['state'] = tk.DISABLED
        self.see('end')


class InformationFrame(MyLabelFrame):
    """情報表示用フレーム
        Labelを持つフレーム
    """
    def __init__(self, lines: int, master=None, **kwargs):
        """初期化
            ラベルをlines個作成し縦に配置する。
        Args:
            lines (int): ラベルの個数
        """
        super().__init__(master=master, **kwargs)
        # ラベルの配置
        self.widget = [tk.Label(self, text='', anchor=tk.W) for i in range(lines)]
        [w.pack(fill=tk.X) for w in self.widget]

    def write(self, msg: list):
        """ラベルへのテキスト設定
            すべてのラベルのtextを消去してからmsgに書き換える

        Args:
            msg (list): メッセージ文字列のリスト
        """
        [w.config(text='') for w in self.widget]
        [w.config(text=text) for w, text in zip(self.widget, msg)]


class SelectMeanTimeFrame(MyLabelFrame):
    """集計単位の選択フレーム
    """
    def __init__(self, master=None, **kwargs):
        super().__init__(master=master, text='集計単位', **kwargs)

        global var_mean_time
        self.var_mean_time = var_mean_time
        self.cb = MyCombobox(
            master=self,
            values=list(MEAN_TIMES.keys()),
            textvariable=self.var_mean_time,
        )
        self.cb.current(list(MEAN_TIMES.keys()).index('1分平均'))         # 初期値を設定
        self.cb.grid(row=0, column=0)


class SelectOutputPeriodFrame(MyLabelFrame):
    """グラフ出力の対象期間（日付）の選択フレーム
    """
    def __init__(self, dates=None, master=None, **kwargs):
        super().__init__(master=master, text='対象期間', **kwargs)

        global var_from, var_to
        self.var_from = var_from
        self.var_to = var_to

        # 開始日
        self.cb_from = MyCombobox(
            master=self, textvariable=self.var_from, state=tk.DISABLED,
        )
        self.cb_from.bind('<<ComboboxSelected>>', self.check_var_to)
        # self.cb_from.bind('<MouseWheel>', self.check_var_to)
        self.cb_from.grid(row=0, column=0)

        # 間の '～'
        tk.Label(master=self, text='～').grid(row=0, column=1)

        # 終了日
        self.cb_to = MyCombobox(
            master=self, textvariable=self.var_to, state=tk.DISABLED,
        )
        self.cb_to.bind('<<ComboboxSelected>>', self.check_var_from)
        # self.cb_to.bind('<MouseWheel>', self.check_var_from)
        self.cb_to.grid(row=0, column=2)

        # 日付の選択肢のセット
        if dates is not None:
            self.set_values(dates)

    def set_values(self, dates):
        self.cb_from['values'] = [str(d) for d in dates]
        self.cb_from['state'] = tk.NORMAL
        self.cb_from.current(0)  # 初期値を設定

        self.cb_to['values'] = [str(d) for d in dates]
        self.cb_to['state'] = tk.NORMAL
        self.cb_to.current(len(dates)-1)  # 初期値を設定

    # from の日付が to を超えたら to の値を修正する
    def check_var_to(self, event=None):
        if self.var_from.get() > self.var_to.get():
            self.var_to.set(self.var_from.get())

    # to の日付が from を下回ったら from の値を修正する
    def check_var_from(self, event=None):
        if self.var_from.get() > self.var_to.get():
            self.var_from.set(self.var_to.get())


class SelectAxisScaleFrame(MyLabelFrame):
    """縦軸のスケールを指定するフレーム
    """
    def __init__(self, master=None, **kwargs):
        super().__init__(master=master, text='縦軸の設定', **kwargs)

        global var_axis_unit, var_axis_type, var_axis_value
        self.var_axis_unit = var_axis_unit
        self.var_axis_type = var_axis_type
        self.var_axis_value = var_axis_value
        # 縦軸のスケールの辞書
        self.AXIS_VALUES = {}
        self.AXIS_VALUES.update({f'{i} Mbps': int(i*1e6) for i in range(1, 10, 1)})
        self.AXIS_VALUES.update({f'{i} Mbps': int(i*1e6) for i in range(10, 100, 10)})
        self.AXIS_VALUES.update({f'{i} Mbps': int(i*1e6) for i in range(100, 1000, 100)})
        self.AXIS_VALUES.update({f'{i} Gbps': int(i*1e9) for i in range(1, 11, 1)})
        # 縦軸の単位とspinboxの増分の辞書
        self.AXIS_UNITS = {
            'bps': int(1e3),
            'kbps': int(100e3),
            'Mbps': int(1e6),
            'Gbps': int(1e9),
        }

        # 子フレーム：単位 ====================
        lf = MyLabelFrame(self, text='単位')
        lf.pack(anchor=tk.W, fill=tk.X)
        for text in self.AXIS_UNITS.keys():
            tk.Radiobutton(
                master=lf, text=text, value=text, variable=self.var_axis_unit,
                command=self.set_increment
            ).pack(anchor=tk.W, side=tk.LEFT)

        # 子フレーム：スケール ====================
        lf = MyLabelFrame(self, text='スケール')
        lf.pack(anchor=tk.W, fill=tk.X)

        # 1列目、自動 or 固定 or 指定のラジオボタン
        for row, (text, value) in enumerate([['自動', 'auto'], ['固定', 'fix'], ['指定', 'specified']]):
            tk.Radiobutton(
                master=lf, text=text, value=value, variable=self.var_axis_type,
                command=self.change_state
            ).grid(row=row, column=0, sticky=tk.NW)

        # 1行/2列目、固定値の選択リスト
        self.cb = MyCombobox(
            master=lf,
            values=list(self.AXIS_VALUES.keys()),
            state=tk.DISABLED,
        )
        self.cb.current(9)  # 初期値を指定
        self.cb.bind('<<ComboboxSelected>>', self.set_var_axis_value)
        # self.cb.bind('<MouseWheel>', self.set_var_axis_value)
        self.cb.grid(row=1, column=1, sticky=tk.W)

        # 2行/2列目、指定値の入力欄
        self.sb = MySpinbox(
            master=lf, from_=1e6, to=10e9, increment=self.AXIS_UNITS[self.var_axis_unit.get()],
            textvariable=self.var_axis_value,
            command=self.spin_changed,
            state=tk.DISABLED,
        )
        # self.sb.bind('<MouseWheel>', self.wheel)
        self.sb.grid(row=2, column=1, sticky=tk.W)
        tk.Label(lf, text='bps').grid(row=2, column=2)  # 単位を表示

        # 固定値の初期値に合わせて値を設定
        self.set_var_axis_value()

    def wheel(self, event):
        increment = int(self.sb.config('increment')[-1])  # incrementの現在値を抽出
        value = self.var_axis_value.get()
        if (event.delta > 0):  # 上向きホイール
            value += increment
        elif (event.delta < 0):  # 下向きホイール
            value -= increment
        if value <= 0:
            value = increment
        self.var_axis_value.set(value)

    def set_var_axis_value(self, event=None):
        self.var_axis_value.set(self.AXIS_VALUES[self.cb.get()])

    # spinboxのボタンが押されたときに値をチェック
    def spin_changed(self):
        try:
            self.var_axis_value.get()
        except Exception:
            self.var_axis_value.set(1)
        if self.var_axis_value.get() < 1:  # 0より下の値を入力した時、1にする
            self.var_axis_value.set(1)

    # spinboxの増分を設定
    def set_increment(self):
        self.sb['increment'] = self.AXIS_UNITS[self.var_axis_unit.get()]

    # チェックボックスに合わせて他のウィジェットのstateを変更する
    def change_state(self):
        if self.var_axis_type.get() == 'fix':
            self.cb['state'] = 'readonly'
            self.sb['state'] = tk.DISABLED
            self.set_var_axis_value()
        elif self.var_axis_type.get() == 'specified':
            self.cb['state'] = tk.DISABLED
            self.sb['state'] = tk.NORMAL
        else:
            self.cb['state'] = tk.DISABLED
            self.sb['state'] = tk.DISABLED


class ButtonFrame(tk.Frame):
    def __init__(self, target, file_info, period, msg, filemenu, master=None, **kwargs):
        super().__init__(master=master)

        global var_mean_time, var_axis_unit, var_from, var_to
        self.var_mean_time = var_mean_time
        self.var_axis_unit = var_axis_unit
        self.var_from = var_from
        self.var_to = var_to
        self.TargetFrame = target
        self.FileInfoFrame = file_info
        self.PeriodFrame = period
        self.MsgFrame = msg  # メッセージフレーム
        self.filemenu = filemenu
        self.df = pd.DataFrame()
        # 読込ボタン
        width = len('ファイル読込') * 2
        self.ReadButton = tk.Button(
            self,
            text='ファイル読込',
            width=width,
            command=self.read_stg_thread,
        )
        # self.ReadButton.pack(side=tk.LEFT, padx=2, pady=2)
        # プレビューボタン
        self.PreviewButton = tk.Button(
            self,
            text='プレビュー',
            width=width,
            command=self.preview_graph,
            state=tk.DISABLED,
        )
        self.PreviewButton.pack(side=tk.LEFT, padx=2, pady=2)
        # 実行ボタン
        self.DrawButton = tk.Button(
            self,
            text='グラフ表示',
            width=width,
            command=self.output_graph,
            state=tk.DISABLED,
        )
        self.DrawButton.pack(side=tk.LEFT, padx=2, pady=2)
        # 終了ボタン
        self.QuitButton = tk.Button(
            self,
            text='終了',
            width=width,
            command=self.abort
        )
        # self.QuitButton.pack(side=tk.LEFT, padx=2, pady=2)

    def abort(self):
        plt.close('all')
        root.destroy()

    def read_stg_thread(self):
        th = threading.Thread(target=self.read_stg, args=())
        th.start()

    def read_stg(self):
        # ファイルダイアログを開く
        filetypes = [('STGローテーションファイル', '*.csv;*.csv.*'), ('すべて', '*'), ]
        csv_filenames = filedialog.askopenfilenames(filetypes=filetypes, initialdir='.',
                                                    title='CSVファイルを選択')
        # ファイル指定がなければ終了
        if csv_filenames == '':
            return

        self.MsgFrame.write(f'\n{now()} CSVファイル読込開始（{len(csv_filenames)} files）\n')

        # CSVファイルのチェック
        for idx, filename in enumerate(csv_filenames):
            line = ''
            # ファイルを開いて1行読み込み
            try:
                with open(filename, 'r', encoding='utf-8') as f:
                    line = f.readline().rstrip()  # 1行読み込み
            except UnicodeDecodeError as err:
                self.MsgFrame.write(f'Error!：文字コードエラー\n  {filename}\n')
                messagebox.showerror('文字コードエラー', f'文字コードがUTF-8ではありません\n{filename}\n{err}')
                return
            except Exception as err:
                self.MsgFrame.write(f'Error!：ファイルオープンエラー\n  {filename}\n')
                messagebox.showerror('ファイルオープンエラー', f'ファイルが開けません\n{filename}\n{err}')
                return

            # チェック１：STGのファイルであることのチェック
            #   行頭がSTGでカンマ区切りで5カラムあること
            columns = line.split(',')
            if line.startswith('STG') is False or len(columns) != 5:
                self.MsgFrame.write(f'Error!：ファイルフォーマットエラー\n  {filename}\n')
                messagebox.showerror(
                    'ファイルフォーマットエラー',
                    f'STGのCSVファイルではありません\n{filename}'
                )
                return
            # ターゲットアドレスを取得
            m = re.match('Target Address:(.+)', columns[1])
            if not m:
                self.MsgFrame.write(f'Error!：ファイルフォーマットエラー\n  {filename}\n')
                messagebox.showerror(
                    'ファイルフォーマットエラー',
                    f'STGのCSVファイルではありません\n{filename}'
                )
                return
            self.target_ip = m.group(1)

            # チェック２：Target情報が前に読み込んだファイルと一致するかチェック
            if idx == 0:  # ファイル1個目
                target = columns[1:]
            elif target != columns[1:]:
                self.MsgFrame.write(f'Error!：ファイル指定エラー\n  {filename}\n')
                messagebox.showerror(
                    'ファイル指定エラー',
                    f'{os.path.basename(filename)} の対象情報が一致しません'
                )
                return

        # CSVファイルの読込
        self.ReadButton['state'] = tk.DISABLED  # ReadButtonをロック
        self.DrawButton['state'] = tk.DISABLED  # DrawButtonをロック
        self.PreviewButton['state'] = tk.DISABLED
        self.filemenu.entryconfigure('CSVファイル読込', state=tk.DISABLED)
        self.filemenu.entryconfigure('CSVファイル出力', state=tk.DISABLED)
        t = ExecTime()

        # CSVファイルをDataFrameとして読み込み、self.dfに結合する
        self.df = pd.DataFrame()
        for idx, filename in enumerate(csv_filenames):
            self.MsgFrame.write(f' [{idx+1}/{len(csv_filenames)}] "{filename}" ... ')
            df = pd.read_csv(
                filename,
                encoding='SHIFT-JIS',                       # 文字コードを指定
                header=1,                                   # 0行目（最初の行）を読み飛ばす
                names=['date', 'uptime', 'recv', 'send'],   # カラム名を設定
            )
            # STGのバグでAugがAvgになっているので、置換して日時認識する
            df['date'] = pd.to_datetime(df['date'].str.replace('Avg', 'Aug'))
            # uptimeが0の行は読み取り失敗のため削除する
            df.drop(df.query('uptime == 0').index, inplace=True)
            # uptimeの列を削除する
            df.drop('uptime', axis=1, inplace=True)
            self.df = pd.concat([self.df, df])
            self.MsgFrame.write(f'{t.laptime:.3f} sec\n')

        self.MsgFrame.write(f'{now()} CSVファイル読込完了\n')

        # カレントディレクトの変更
        os.chdir(os.path.dirname(csv_filenames[0]))
        # self.MsgFrame.write(f' ファイル出力先：{os.getcwd()}\n')
        # 重複行を削除する
        self.df.drop_duplicates(inplace=True)
        # 'date'をインデックスにする
        self.df.set_index('date', inplace=True)
        # インデックス順（日時）でソートする
        self.df.sort_index(inplace=True)
        # 1行目を削除する（取得値が非常に大きい場合があるため）
        self.df.drop(self.df.index[0], inplace=True)
        # delta_timeを計算する
        self.df['delta_time'] = self.df.index.to_series().diff().dt.total_seconds()

        # 機器情報出力
        self.TargetFrame.write(target)
        # ファイル情報出力
        recv = self.df['recv'] * 8 // self.df['delta_time']
        send = self.df['send'] * 8 // self.df['delta_time']
        delta = self.df['delta_time']
        text = [
            f'開始日時: {str(self.df.index[0])[:-7]}',
            f'終了日時: {str(self.df.index[-1])[:-7]}',
            f'取得間隔: {delta.min():,.2} ～ {delta.max():,.2} 秒',
            f'取得行数: {self.df.shape[0]:,}',
            f'受信帯域: 最大 {int(recv.max()):,} bps',
            f'送信帯域: 最大 {int(send.max()):,} bps',
        ]
        self.FileInfoFrame.write(text)
        # 期間情報設定
        self.PeriodFrame.set_values(sorted(set(self.df.index.date)))

        self.ReadButton['state'] = tk.NORMAL  # ReadButtonをロック解除
        self.DrawButton['state'] = tk.NORMAL  # DrawButtonをロック解除
        self.PreviewButton['state'] = tk.NORMAL  # PreviewButtonをロック解除
        self.filemenu.entryconfigure('CSVファイル読込', state=tk.NORMAL)
        self.filemenu.entryconfigure('CSVファイル出力', state=tk.NORMAL)

        self.preview_graph()

    def _resample_df(self) -> tuple:
        """
        リサンプルしたDataFrameと各種変数を返す
        """
        rule = MEAN_TIMES[self.var_mean_time.get()]
        axis_unit = self.var_axis_unit.get()

        # 指定時間で集約
        if rule == 'org':
            df = self.df.copy()
        else:
            df = self.df.resample(rule=rule).sum()
            # df['delta_time'] = df.index.to_series().diff().dt.total_seconds()

        # 指定期間を抽出
        df = df[self.var_from.get():self.var_to.get()]

        # スループットを計算
        if axis_unit == 'bps':
            div_unit = 1
        elif axis_unit == 'kbps':
            div_unit = int(1e3)
        elif axis_unit == 'Mbps':
            div_unit = int(1e6)
        elif axis_unit == 'Gbps':
            div_unit = int(1e9)

        recv_unit = 'recv_' + axis_unit
        send_unit = 'send_' + axis_unit
        df[recv_unit] = df['recv'] * 8 // df['delta_time'] / div_unit
        df[send_unit] = df['send'] * 8 // df['delta_time'] / div_unit

        # # CSVファイル出力
        # output_columns = ['delta_time', recv_unit, send_unit]
        # df[output_columns].to_csv(f'{self.target_ip}_{var_mean_time.get()}.csv', sep=',')

        # 送受信の最大値と発生日時を調べる
        recv_max = df[recv_unit].max()
        send_max = df[send_unit].max()
        recv_max_date = re.sub(r'\.\d+$', '', str(df[df[recv_unit] == recv_max].index.tolist()[0]))
        send_max_date = re.sub(r'\.\d+$', '', str(df[df[send_unit] == send_max].index.tolist()[0]))

        # 送受信の最大値の文字列を作成、MbpsとGbpsは少数点3桁表示
        if axis_unit == 'Mbps' or axis_unit == 'Gbps':
            recv_max_str = f'{recv_max:,.3f}'
            send_max_str = f'{send_max:,.3f}'
        else:
            recv_max_str = f'{int(recv_max):,}'
            send_max_str = f'{int(send_max):,}'

        strlen_max = max(len(recv_max_str), len(send_max_str))

        str1 = f'受信MAX: {recv_max_str:>{strlen_max}} {axis_unit} ({recv_max_date})'
        str2 = f'送信MAX: {send_max_str:>{strlen_max}} {axis_unit} ({send_max_date})'

        return (df, recv_unit, send_unit, axis_unit, div_unit, str1, str2)

    def _adjust_axes(self, ax, axis_unit, div_unit, r_max, s_max):
        # X軸ラベル
        ax.set_xlabel('日時')
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d %H:%M'))
        ax.xaxis.set_minor_locator(AutoMinorLocator(6))
        # Y軸ラベル
        ax.set_ylabel(axis_unit)
        ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, loc: f'{x:,.1f}'))
        ax.yaxis.set_minor_locator(AutoMinorLocator())
        # グリッド線
        ax.grid(b=True, axis='both', which='major', color='gray', linestyle='--', alpha=0.9)
        ax.grid(b=True, axis='both', which='minor', color='gray', linestyle='--', alpha=0.2)
        # Y軸のスケール
        if var_axis_type.get() == 'auto':
            ax.set_ylim(0,)
        else:
            ax.set_ylim([0, var_axis_value.get() // div_unit])

        # 送受信の最大値をグラフ上にテキスト表示
        ax.text(0.05, 0.9, r_max + '\n' + s_max, family='ms gothic', transform=ax.transAxes)

    def output_graph(self):
        """
        指定の時間でスループットを計算してグラフ表示する
        """
        (df, recv_unit, send_unit, axis_unit, div_unit, r_max, s_max) = self._resample_df()

        # グラフ描画
        ax = df.plot(
            grid=True,
            y=[recv_unit, send_unit],
            title=f'{self.target_ip} スループット（{var_mean_time.get()}）',
            rot=30,
            x_compat=True
            )

        # axesの見栄えを調整する
        self._adjust_axes(ax, axis_unit, div_unit, r_max, s_max)

        plt.show()

    def preview_graph(self):
        """
        グラフをプレビューする
        """
        (df, recv_unit, send_unit, axis_unit, div_unit, r_max, s_max) = self._resample_df()

        # グラフ描画
        ax.cla()
        df.plot(
            ax=ax,
            grid=True,
            y=[recv_unit, send_unit],
            title=f'{self.target_ip} スループット（{var_mean_time.get()}）',
            rot=30,
            x_compat=True
            )

        # axesの見栄えを調整する
        self._adjust_axes(ax, axis_unit, div_unit, r_max, s_max)

        canvas.draw()

    def output_csv(self):
        """
        CSVファイルを出力する
        """
        (df, recv_unit, send_unit, *_) = self._resample_df()

        # CSVファイル出力
        output_fname = f'{self.target_ip}_{var_mean_time.get()}.csv'
        output_columns = ['delta_time', recv_unit, send_unit]
        df[output_columns].to_csv(output_fname, sep=',')
        self.MsgFrame.write(f'\n{now()} CSVファイル出力\n')
        self.MsgFrame.write(f' "{os.path.abspath(output_fname)}"\n')


class ExecTime():
    """コマンドの実行時間を測定する"""
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
        print(f'{self.laptime:.3f} sec')


# =================================================================
# メインルーチン
# =================================================================
if __name__ == '__main__':
    root = tk.Tk()
    root.withdraw()

    # メニューバー
    menubar = tk.Menu(master=root)
    root.config(menu=menubar)
    # File Menu
    filemenu = tk.Menu(menubar, tearoff=0)
    filemenu.add_command(label='CSVファイル読込')
    filemenu.add_command(label='CSVファイル出力')
    filemenu.add_separator()
    filemenu.add_command(label='終了', command=quit)
    # Add
    menubar.add_cascade(label='ファイル', underline=0, menu=filemenu)

    # ウィジェット共通の変数
    var_axis_unit = tk.StringVar(value='Mbps')  # 縦軸の単位 bps / kbps / Mbps / Gbps
    var_axis_type = tk.StringVar(value='auto')  # 縦軸の指定方法 auto / fix / specified
    var_axis_value = tk.IntVar()                # 縦軸の高さ
    var_mean_time = tk.StringVar()             # 集計時間単位（n分平均）
    var_from = tk.StringVar()             # 集計開始日
    var_to = tk.StringVar()             # 集計終了日

    # tkinterのウィジェット設定

    # 機器情報
    target_frame = InformationFrame(master=root, lines=6, text='機器情報')
    target_frame.grid(row=0, column=0)

    # ファイル情報
    fileinfo_frame = InformationFrame(master=root, lines=6, text='CSV情報')
    fileinfo_frame.grid(row=0, column=1)

    # 集計単位の選択
    SelectMeanTimeFrame(master=root).grid(row=1, column=0)

    # 期間指定
    period_frame = SelectOutputPeriodFrame(master=root)
    period_frame.grid(row=1, column=1)

    # 縦軸スケールの選択
    SelectAxisScaleFrame(master=root).grid(row=2, column=0, columnspan=2)

    # メッセージ表示窓
    msg_frame = MyScrolledText(master=root, width=80, height=10)
    msg_frame.grid(row=3, column=0, columnspan=2)

    # 実行ボタン
    button_frame = ButtonFrame(
        target_frame,
        fileinfo_frame,
        period_frame,
        msg_frame,
        filemenu,
        master=root,
    )
    button_frame.grid(row=4, column=0, columnspan=2, ipady=2, padx=2, pady=2)

    # プレビュー表示用のcanvasの作成
    fig = Figure()
    ax = fig.add_subplot()
    ax.grid(b=True, axis='both', which='both', color='gray', linestyle='--', alpha=0.5)
    fig.subplots_adjust(top=0.9, bottom=0.19, left=0.14)

    canvas = FigureCanvasTkAgg(fig, master=root)
    canvas.draw()
    # toolbarを表示するときは、rowspan=4にする。非表示の場合5
    canvas.get_tk_widget().grid(row=0, column=2, rowspan=4, sticky=tk.NSEW)

    toolbar = NavigationToolbar2Tk(canvas, root, pack_toolbar=False)
    toolbar.update()
    toolbar.grid(row=4, column=2, sticky=tk.W)

    # ファイルメニュー
    filemenu.entryconfigure('CSVファイル読込', command=button_frame.read_stg_thread, state=tk.NORMAL)
    filemenu.entryconfigure('CSVファイル出力', command=button_frame.output_csv, state=tk.DISABLED)

    root.title(f'STG Graph Plot  ver. {__version__}')
    root.resizable(width=False, height=False)
    root.deiconify()
    root.mainloop()
