import streamlit as st
import pandas as pd
import os
import glob
import plotly.graph_objects as go
from plotly.subplots import make_subplots


default_folder_path = r'\source'


def visualize_backtest_results(folder_path, chart_height=6, mdd_alpha=0.3):
    """
    可视化回测结果并展示统计数据

    Parameters:
    folder_path (str): 包含回测结果文件的文件夹路径
    chart_height (int): 图表高度
    mdd_alpha (float): 回撤透明度
    """

    # 查找nv_total.csv文件
    nv_files = glob.glob(os.path.join(folder_path, '*nv_total.csv'))
    if not nv_files:
        st.error("未找到以 'nv_total.csv' 结尾的文件")
        return

    # 读取净值数据
    nv_file = nv_files[0]
    nv_df = pd.read_csv(nv_file)

    # 确保时间列存在
    if 'dt' not in nv_df.columns:
        st.error("净值文件中未找到 'dt' 时间列")
        return

    # 转换时间列格式
    nv_df['dt'] = pd.to_datetime(nv_df['dt'])
    nv_df = nv_df.sort_values('dt')

    # 查找以'acc'结尾的列
    acc_columns = [col for col in nv_df.columns if col.endswith('acc')]
    if not acc_columns:
        st.error("未找到以 'acc' 结尾的列")
        return

    # 创建交互式图表
    fig = make_subplots(specs=[[{"secondary_y": True}]])

    # 绘制净值曲线
    for acc_col in acc_columns:
        # 检查是否包含'bh'，如果是则使用特殊名称和颜色
        if 'bh' in acc_col.lower():
            display_name = 'Buy Hold'
            line_color = 'lightblue'
        else:
            display_name = acc_col
            line_color = None  # 使用默认颜色

        fig.add_trace(
            go.Scatter(
                x=nv_df['dt'],
                y=nv_df[acc_col],
                mode='lines',
                name=display_name,
                line=dict(width=2, color=line_color) if line_color else dict(width=2),
                hovertemplate=
                "<b>%{fullData.name}</b><br>" +
                "Datetime: %{x|%Y-%m-%d}<br>" +
                "Net Value: %{y:.6f}<br>" +
                "<extra></extra>"
            )
        )

    # 添加训练集结束时间点的垂直虚线（2023-12-29）
    train_end_date = "2023-12-29"
    fig.add_vline(
        x=train_end_date,
        line_dash="dash",
        line_color="black",
        line_width=1
    )

    # 添加标注
    fig.add_annotation(
        x=train_end_date,
        y=1,
        xref="x",
        yref="paper",
        text="End of training set",
        showarrow=False,
        yanchor="bottom",
        font=dict(color="black", size=12),
        bgcolor="white"
    )

    # 添加0轴参考线
    fig.add_hline(
        y=0,
        line_dash="solid",
        line_color="black",
        line_width=1
    )

    # 绘制最大回撤（较淡的阴影）
    if 'mdd' in nv_df.columns:
        fig.add_trace(
            go.Scatter(
                x=nv_df['dt'],
                y=nv_df['mdd'],
                mode='lines',
                name='Draw Down',
                line=dict(width=0),  # 隐藏线条
                fill='tozeroy',
                fillcolor=f'rgba(128, 128, 128, {mdd_alpha})',  # 灰色填充
                hovertemplate=
                "<b>Draw Down</b><br>" +
                "Datetime: %{x|%Y-%m-%d}<br>" +
                "Draw Down: %{y:.6f}<br>" +
                "<extra></extra>"
            ),
            secondary_y=True
        )

    # 设置图表布局
    fig.update_layout(
        title='Backtest NV and MDD',
        xaxis_title='dt',
        yaxis_title='nv',
        height=chart_height * 100,  # 转换为像素
        hovermode='x unified',  # 统一悬停模式
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        ),
        # 设置网格线
        yaxis=dict(
            showgrid=True,
            gridcolor='lightgray',
            gridwidth=1
        ),
        yaxis2=dict(
            showgrid=False  # 副轴不显示网格线，避免重叠
        )
    )

    # # 设置x轴标签
    # fig.update_xaxes(
    #     tickformat="%Y-%m",  # 显示格式为年-月
    #     dtick="M4",  # 每4个月一个刻度
    #     tickangle=45  # 刻度标签角度
    # )

    # 设置y轴标题
    fig.update_yaxes(title_text="nv", secondary_y=False, tickfont=dict(color='black'))
    fig.update_yaxes(title_text="mdd", secondary_y=True, tickfont=dict(color='lightgray'))

    # 在Streamlit中显示图表
    st.plotly_chart(fig, width='stretch')

    # 查找并显示统计数据
    margin_files = glob.glob(os.path.join(folder_path, '*margin.csv'))
    if not margin_files:
        st.warning("未找到 'all' 路径下以 'margin.csv' 结尾的文件")
        return

    margin_file = margin_files[0]
    margin_df = pd.read_csv(margin_file)
    margin_df = margin_df.iloc[[-1]].copy()

    # 显示统计数据表
    st.subheader("回测统计指标")

    # 筛选需要显示的列
    required_columns = [
        '开始日期', '结束日期', '单笔收益(bp)', '持仓交易时间（分钟）',
        '交易次数', '净值累计收益', '夏普比率', '最大回撤', '卡玛比率',
        '交易胜率', '信息比率', '年化收益率', '单笔盈亏比', 'margin_mean'
    ]

    # 只显示存在的列
    existing_columns = [col for col in required_columns if col in margin_df.columns]
    if existing_columns:
        display_df = margin_df[existing_columns].copy()

        # 格式化数据显示
        format_dict = {}
        for col in existing_columns:
            if '单笔' in col and '收益' in col:
                format_dict[col] = "{:.2f}"
            elif '日期' in col:
                format_dict[col] = "{:%Y-%m-%d}"
            elif any(keyword in col for keyword in ['收益', '回撤', '波动率', '比例', '胜率']):
                format_dict[col] = "{:.2%}"
            elif any(keyword in col for keyword in ['次数', '日数', '数目']):
                format_dict[col] = "{:.0f}"
            else:
                format_dict[col] = "{:.2f}"

        # 应用格式化
        for col, fmt in format_dict.items():
            if col in display_df.columns:
                if '日期' in col:
                    # 日期列需要特殊处理
                    display_df[col] = pd.to_datetime(display_df[col]).dt.strftime('%Y-%m-%d')
                else:
                    # 数值列格式化
                    display_df[col] = display_df[col].map(lambda x: fmt.format(x))

        st.dataframe(display_df)
    else:
        st.warning("统计文件中未找到指定的列")
        # 显示所有可用列供参考
        st.write("可用的列:", margin_df.columns.tolist())


def visualize_multiple_backtest_results(folder_paths):
    """
    对比多个回测结果

    Parameters:
    folder_paths (list): 回测结果文件夹路径列表
    """
    if not folder_paths:
        st.warning("请选择至少一个回测文件夹")
        return

    # 创建对比图表
    fig = go.Figure()

    # 存储所有统计数据用于表格展示
    all_stats_data = []

    for i, folder_path in enumerate(folder_paths):
        # 处理每个回测结果
        nv_files = glob.glob(os.path.join(folder_path, '*nv_total.csv'))
        if not nv_files:
            st.warning(f"文件夹 {folder_path} 中未找到 'nv_total.csv' 文件")
            continue

        nv_file = nv_files[0]
        nv_df = pd.read_csv(nv_file)

        if 'dt' not in nv_df.columns:
            st.warning(f"文件夹 {folder_path} 的净值文件中未找到 'dt' 列")
            continue

        nv_df['dt'] = pd.to_datetime(nv_df['dt'])
        nv_df = nv_df.sort_values('dt')

        acc_columns = [col for col in nv_df.columns if col.endswith('acc')]
        if not acc_columns:
            st.warning(f"文件夹 {folder_path} 中未找到以 'acc' 结尾的列")
            continue

        # 使用第一个acc列为对比基准
        acc_col = acc_columns[0]
        fig.add_trace(
            go.Scatter(
                x=nv_df['dt'],
                y=nv_df[acc_col],
                mode='lines',
                name=f'{os.path.basename(folder_path)}_{acc_col}',
                line=dict(width=2),
                hovertemplate=
                "<b>%{fullData.name}</b><br>" +
                "时间: %{x|%Y-%m-%d}<br>" +
                "净值: %{y:.6f}<br>" +
                "<extra></extra>"
            )
        )

        # 获取统计数据
        margin_files = glob.glob(os.path.join(folder_path, '*margin.csv'))
        if margin_files:
            margin_file = margin_files[0]
            margin_df = pd.read_csv(margin_file)
            if not margin_df.empty:
                stats_row = margin_df.iloc[-1].copy()
                stats_row['回测名称'] = os.path.basename(folder_path)
                all_stats_data.append(stats_row)

    # 设置图表布局
    fig.update_layout(
        title='Multi-Backtest Results Comparison',
        xaxis_title='dt',
        yaxis_title='nv',
        height=600,
        hovermode='x unified'
    )

    st.plotly_chart(fig, width='stretch')

    # 显示对比统计数据
    if all_stats_data:
        st.subheader("回测结果对比表")
        compare_df = pd.DataFrame(all_stats_data)
        required_columns = ['回测名称'] + [
            '开始日期', '结束日期', '单笔收益(bp)', '持仓交易时间（分钟）',
            '交易次数', '净值累计收益', '夏普比率', '最大回撤', '卡玛比率',
            '交易胜率', '信息比率', '年化收益率', '单笔盈亏比', 'margin_mean'
        ]
        existing_columns = [col for col in required_columns if col in compare_df.columns]
        if existing_columns:
            display_df = compare_df[existing_columns].copy()

            # 格式化数据显示
            format_dict = {}
            for col in existing_columns:
                if '名称' in col:
                    format_dict[col] = "{}"  # 字符串格式化
                elif '单笔' in col and '收益' in col:
                    format_dict[col] = "{:.2f}"
                elif '日期' in col:
                    format_dict[col] = "{:%Y-%m-%d}"
                elif any(keyword in col for keyword in ['收益', '回撤', '波动率', '比例', '胜率']):
                    format_dict[col] = "{:.2%}"
                elif any(keyword in col for keyword in ['次数', '日数', '数目']):
                    format_dict[col] = "{:.0f}"
                else:
                    format_dict[col] = "{:.2f}"

            # 应用格式化
            for col, fmt in format_dict.items():
                if col in display_df.columns:
                    if '日期' in col:
                        # 日期列需要特殊处理
                        display_df[col] = pd.to_datetime(display_df[col]).dt.strftime('%Y-%m-%d')
                    else:
                        # 数值列格式化
                        try:
                            display_df[col] = display_df[col].map(lambda x: fmt.format(x))
                        except Exception:
                            # 如果转换失败，保持原始值
                            pass

            st.dataframe(display_df)
        else:
            st.dataframe(compare_df)


def main():
    st.set_page_config(page_title="回测结果可视化分析", layout="wide")

    st.title("回测结果可视化分析")
    st.markdown("""
        本工具用于可视化回测结果，包括净值曲线和关键统计指标。
        """)

    # 侧边栏配置面板
    st.sidebar.header("应用查看设置")

    # 图表配置
    st.sidebar.subheader("图表配置")
    chart_height = st.sidebar.slider("图表高度", 4, 10, 6)
    mdd_alpha = st.sidebar.slider("回撤透明度", 0.1, 0.8, 0.15)

    # 模式选择
    mode = st.sidebar.radio("选择模式", ["单策略分析", "多策略对比"])

    if mode == "单策略分析":
        # 单文件查看模式
        st.header("单回测结果查看")

        # 或者使用文件夹选择器（如果在本地运行）
        st.markdown("### 选择本地文件夹")
        if os.path.exists(default_folder_path):
            # 获取所有文件夹并按修改时间排序
            all_dirs = []
            for d in os.listdir(default_folder_path):
                dir_path = os.path.join(default_folder_path, d)
                if os.path.isdir(dir_path) and not d.startswith('.'):
                    # 获取文件夹的修改时间
                    mod_time = os.path.getmtime(dir_path)
                    all_dirs.append((d, mod_time))

            # 按修改时间降序排序（最新的在前）
            all_dirs.sort(key=lambda x: x[1], reverse=True)
            folder_options = [d[0] for d in all_dirs]

        # 如果有文件夹选项，则创建下拉框
        if folder_options:
            # 默认选择最新的文件夹
            default_selection = folder_options[0] if folder_options else ""
            selected_folder_name = st.selectbox(
                "选择本地文件夹:",
                options=folder_options,
                index=0 if folder_options else 0,
                key="local_folder_select"
            )

            # 构建完整路径
            local_folder = os.path.join(default_folder_path, selected_folder_name) if selected_folder_name else ""
        else:
            # 如果没有文件夹选项，显示提示信息
            st.info(f"{default_folder_path}目录下没有可选择的文件夹")
            local_folder = ""
            selected_folder_name = ""

        if st.button("生成分析报告") and local_folder:
            if os.path.exists(local_folder):
                visualize_backtest_results(local_folder, chart_height, mdd_alpha)
            else:
                st.error("指定的文件夹路径不存在，请检查后重试")

        st.markdown("---")
        st.markdown("### 输入文件夹路径")
        # 添加文件夹路径输入
        folder_path = st.text_input(
            "请输入回测结果文件夹路径:",
            placeholder="例如: ./backtest_results"
        )

        # 添加执行按钮
        if st.button("生成手动路径分析报告") and folder_path:
            if os.path.exists(folder_path):
                visualize_backtest_results(folder_path, chart_height, mdd_alpha)
            else:
                st.error("指定的文件夹路径不存在，请检查后重试")

    else:
        # 多文件对比模式
        st.header("多回测结果对比")

        # 获取当前目录下的所有文件夹作为选项
        current_dir = default_folder_path
        if os.path.exists(current_dir):
            # 获取所有文件夹并按修改时间排序
            all_dirs = []
            for d in os.listdir(current_dir):
                dir_path = os.path.join(current_dir, d)
                if os.path.isdir(dir_path) and not d.startswith('.'):
                    # 获取文件夹的修改时间
                    mod_time = os.path.getmtime(dir_path)
                    all_dirs.append((d, mod_time))

            # 按修改时间降序排序（最新的在前）
            all_dirs.sort(key=lambda x: x[1], reverse=True)
            all_dir_names = [d[0] for d in all_dirs]

            if all_dir_names:
                # 默认选择最新的两个文件夹
                default_dirs = all_dir_names[:2] if len(all_dir_names) >= 2 else all_dir_names
                selected_dirs = st.multiselect(
                    "选择要对比的回测文件夹",
                    all_dir_names,
                    default=default_dirs
                )

                # 构建完整路径
                full_paths = [os.path.join(current_dir, d) for d in selected_dirs]

                if st.button("生成对比报告"):
                    visualize_multiple_backtest_results(full_paths)
            else:
                st.info(f"{default_folder_path}目录下没有可选择的文件夹，请先准备回测数据文件夹")
        else:
            st.error(f"{default_folder_path}目录不存在，请检查路径是否正确")

        st.markdown("---")
        st.markdown("### 手动输入文件夹路径")
        manual_paths = st.text_area(
            "输入多个文件夹路径（每行一个）:",
            height=100,
            placeholder="例如:\n./backtest_1\n./backtest_2\n./backtest_3"
        )

        if st.button("生成手动路径对比报告"):
            if manual_paths.strip():
                paths = [path.strip() for path in manual_paths.split('\n') if path.strip()]
                valid_paths = [path for path in paths if os.path.exists(path)]
                invalid_paths = [path for path in paths if not os.path.exists(path)]

                if invalid_paths:
                    st.warning(f"以下路径不存在: {invalid_paths}")

                if valid_paths:
                    visualize_multiple_backtest_results(valid_paths)
                else:
                    st.error("没有有效的文件夹路径")
            else:
                st.warning("请输入至少一个文件夹路径")


# 主程序入口
if __name__ == "__main__":

    main()
