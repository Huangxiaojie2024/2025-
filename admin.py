import streamlit as st
import pandas as pd
import json
from pathlib import Path
from datetime import datetime
import zipfile
import io

st.set_page_config(
    page_title="揭阳市临床药学分会 - 数据管理后台",
    page_icon="📊",
    layout="wide"
)

DATA_DIR = Path("data_submissions")

def load_all_unit_data():
    """加载所有单位的数据"""
    all_data = {}
    
    if not DATA_DIR.exists():
        return all_data
    
    for unit_dir in DATA_DIR.iterdir():
        if unit_dir.is_dir():
            unit_name = unit_dir.name
            all_data[unit_name] = {}
            
            # 读取各类JSON文件
            for json_file in unit_dir.glob("*.json"):
                category = json_file.stem
                try:
                    with open(json_file, 'r', encoding='utf-8') as f:
                        all_data[unit_name][category] = json.load(f)
                except Exception as e:
                    st.error(f"读取{unit_name}的{category}数据时出错：{str(e)}")
    
    return all_data

def export_all_to_excel(all_data):
    """将所有单位数据导出为一个Excel文件"""
    output = io.BytesIO()
    
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        # 科研立项汇总
        all_projects = []
        for unit_name, unit_data in all_data.items():
            if '科研立项' in unit_data and '科研立项' in unit_data['科研立项']:
                for proj in unit_data['科研立项']['科研立项']:
                    proj_copy = proj.copy()
                    proj_copy['单位名称'] = unit_name
                    all_projects.append(proj_copy)
        
        if all_projects:
            df = pd.DataFrame(all_projects)
            # 调整列顺序
            cols = ['单位名称'] + [col for col in df.columns if col != '单位名称']
            df = df[cols]
            df.to_excel(writer, sheet_name='科研立项汇总', index=False)
        
        # 论文发表汇总
        all_publications = []
        for unit_name, unit_data in all_data.items():
            if '论文发表' in unit_data and '论文发表' in unit_data['论文发表']:
                for pub in unit_data['论文发表']['论文发表']:
                    pub_copy = pub.copy()
                    pub_copy['单位名称'] = unit_name
                    all_publications.append(pub_copy)
        
        if all_publications:
            df = pd.DataFrame(all_publications)
            cols = ['单位名称'] + [col for col in df.columns if col != '单位名称']
            df = df[cols]
            df.to_excel(writer, sheet_name='论文发表汇总', index=False)
        
        # 学术活动汇总
        all_academic = []
        for unit_name, unit_data in all_data.items():
            if '学术活动' in unit_data and '学术活动' in unit_data['学术活动']:
                for act in unit_data['学术活动']['学术活动']:
                    all_academic.append({
                        '单位名称': unit_name,
                        '日期': act['日期'],
                        '活动名称': act['活动名称'],
                        '活动简介': act['活动简介'],
                        '图片数量': len(act['图片'])
                    })
        
        if all_academic:
            df = pd.DataFrame(all_academic)
            df.to_excel(writer, sheet_name='学术活动汇总', index=False)
        
        # 科普活动汇总
        all_popular = []
        for unit_name, unit_data in all_data.items():
            if '科普活动' in unit_data and '科普活动' in unit_data['科普活动']:
                for act in unit_data['科普活动']['科普活动']:
                    all_popular.append({
                        '单位名称': unit_name,
                        '日期': act['日期'],
                        '活动名称': act['活动名称'],
                        '活动简介': act['活动简介'],
                        '图片数量': len(act['图片'])
                    })
        
        if all_popular:
            df = pd.DataFrame(all_popular)
            df.to_excel(writer, sheet_name='科普活动汇总', index=False)
        
        # 技能竞赛汇总
        all_competitions = []
        for unit_name, unit_data in all_data.items():
            if '技能竞赛' in unit_data and '技能竞赛' in unit_data['技能竞赛']:
                for comp in unit_data['技能竞赛']['技能竞赛']:
                    all_competitions.append({
                        '单位名称': unit_name,
                        '日期': comp['日期'],
                        '竞赛名称': comp['竞赛名称'],
                        '竞赛简介': comp['竞赛简介'],
                        '图片数量': len(comp['图片'])
                    })
        
        if all_competitions:
            df = pd.DataFrame(all_competitions)
            df.to_excel(writer, sheet_name='技能竞赛汇总', index=False)
        
        # 获奖情况汇总
        all_awards = []
        for unit_name, unit_data in all_data.items():
            if '获奖情况' in unit_data and '获奖情况' in unit_data['获奖情况']:
                for award in unit_data['获奖情况']['获奖情况']:
                    all_awards.append({
                        '单位名称': unit_name,
                        '日期': award['日期'],
                        '奖项名称': award['奖项名称'],
                        '图片数量': len(award['图片'])
                    })
        
        if all_awards:
            df = pd.DataFrame(all_awards)
            df.to_excel(writer, sheet_name='获奖情况汇总', index=False)
        
        # 单位提交情况统计
        submit_status = []
        for unit_name in all_data.keys():
            unit_data = all_data[unit_name]
            status = {
                '单位名称': unit_name,
                '工作总结': '✓' if '工作总结与计划_info' in unit_data else '✗',
                '学术活动': len(unit_data.get('学术活动', {}).get('学术活动', [])),
                '科普活动': len(unit_data.get('科普活动', {}).get('科普活动', [])),
                '技能竞赛': len(unit_data.get('技能竞赛', {}).get('技能竞赛', [])),
                '获奖情况': len(unit_data.get('获奖情况', {}).get('获奖情况', [])),
                '科研立项': len(unit_data.get('科研立项', {}).get('科研立项', [])),
                '论文发表': len(unit_data.get('论文发表', {}).get('论文发表', []))
            }
            
            # 获取提交时间
            submit_times = []
            for key in unit_data.keys():
                if '提交时间' in unit_data[key]:
                    submit_times.append(unit_data[key]['提交时间'])
            
            status['最后提交时间'] = max(submit_times) if submit_times else '未提交'
            submit_status.append(status)
        
        if submit_status:
            df = pd.DataFrame(submit_status)
            df.to_excel(writer, sheet_name='提交情况统计', index=False)
    
    output.seek(0)
    return output

def main():
    st.title("📊 揭阳市临床药学分会数据管理后台")
    st.markdown("---")
    
    # 加载所有数据
    all_data = load_all_unit_data()
    
    if not all_data:
        st.warning("⚠️ 暂无数据，请等待各单位提交")
        return
    
    # 侧边栏选择
    st.sidebar.header("数据筛选")
    view_mode = st.sidebar.radio(
        "查看模式",
        ["概览统计", "按单位查看", "分类汇总"]
    )
    
    # ========== 概览统计 ==========
    if view_mode == "概览统计":
        st.header("📈 数据概览")
        
        # 统计信息
        col1, col2, col3, col4 = st.columns(4)
        
        total_academic = sum(len(unit.get('学术活动', {}).get('学术活动', [])) 
                           for unit in all_data.values())
        total_popular = sum(len(unit.get('科普活动', {}).get('科普活动', [])) 
                          for unit in all_data.values())
        total_competitions = sum(len(unit.get('技能竞赛', {}).get('技能竞赛', [])) 
                               for unit in all_data.values())
        total_awards = sum(len(unit.get('获奖情况', {}).get('获奖情况', [])) 
                         for unit in all_data.values())
        
        with col1:
            st.metric("提交单位数", len(all_data))
        with col2:
            st.metric("学术活动总数", total_academic)
        with col3:
            st.metric("科普活动总数", total_popular)
        with col4:
            st.metric("技能竞赛总数", total_competitions)
        
        col1, col2, col3 = st.columns(3)
        
        total_projects = sum(len(unit.get('科研立项', {}).get('科研立项', [])) 
                           for unit in all_data.values())
        total_publications = sum(len(unit.get('论文发表', {}).get('论文发表', [])) 
                               for unit in all_data.values())
        
        with col1:
            st.metric("获奖总数", total_awards)
        with col2:
            st.metric("科研立项总数", total_projects)
        with col3:
            st.metric("论文发表总数", total_publications)
        
        st.markdown("---")
        
        # 提交情况表
        st.subheader("各单位提交情况")
        submit_data = []
        for unit_name, unit_data in all_data.items():
            row = {
                '单位名称': unit_name,
                '工作总结': '✓' if '工作总结与计划_info' in unit_data else '✗',
                '学术活动': len(unit_data.get('学术活动', {}).get('学术活动', [])),
                '科普活动': len(unit_data.get('科普活动', {}).get('科普活动', [])),
                '技能竞赛': len(unit_data.get('技能竞赛', {}).get('技能竞赛', [])),
                '获奖情况': len(unit_data.get('获奖情况', {}).get('获奖情况', [])),
                '科研立项': len(unit_data.get('科研立项', {}).get('科研立项', [])),
                '论文发表': len(unit_data.get('论文发表', {}).get('论文发表', []))
            }
            
            # 获取最后提交时间
            submit_times = []
            for key in unit_data.keys():
                if '提交时间' in unit_data[key]:
                    submit_times.append(unit_data[key]['提交时间'])
            row['最后提交时间'] = max(submit_times) if submit_times else '未提交'
            
            submit_data.append(row)
        
        df_submit = pd.DataFrame(submit_data)
        st.dataframe(df_submit, use_container_width=True)
    
    # ========== 按单位查看 ==========
    elif view_mode == "按单位查看":
        st.header("🏥 按单位查看数据")
        
        selected_unit = st.selectbox("选择单位", list(all_data.keys()))
        
        if selected_unit:
            unit_data = all_data[selected_unit]
            
            tabs = st.tabs([
                "工作总结",
                "学术活动",
                "科普活动",
                "技能竞赛",
                "获奖情况",
                "科研立项",
                "论文发表"
            ])
            
            # 工作总结
            with tabs[0]:
                if '工作总结与计划_info' in unit_data:
                    info = unit_data['工作总结与计划_info']
                    st.write(f"**联系人：** {info.get('联系人', '未填写')}")
                    st.write(f"**联系电话：** {info.get('联系电话', '未填写')}")
                    st.write(f"**提交时间：** {info.get('提交时间', '未知')}")
                    
                    if '文件' in info:
                        st.markdown("### 已提交文件")
                        for file_name, file_path in info['文件'].items():
                            st.write(f"- {file_name}: `{file_path}`")
                else:
                    st.info("该单位尚未提交工作总结与计划")
            
            # 学术活动
            with tabs[1]:
                if '学术活动' in unit_data:
                    activities = unit_data['学术活动'].get('学术活动', [])
                    if activities:
                        for idx, act in enumerate(activities, 1):
                            with st.expander(f"{idx}. {act['活动名称']} ({act['日期']})"):
                                st.write(f"**简介：** {act['活动简介']}")
                                st.write(f"**图片：** {len(act['图片'])}张")
                                for img_path in act['图片']:
                                    st.write(f"- `{img_path}`")
                    else:
                        st.info("该单位尚未提交学术活动")
                else:
                    st.info("该单位尚未提交学术活动")
            
            # 科普活动
            with tabs[2]:
                if '科普活动' in unit_data:
                    activities = unit_data['科普活动'].get('科普活动', [])
                    if activities:
                        for idx, act in enumerate(activities, 1):
                            with st.expander(f"{idx}. {act['活动名称']} ({act['日期']})"):
                                st.write(f"**简介：** {act['活动简介']}")
                                st.write(f"**图片：** {len(act['图片'])}张")
                    else:
                        st.info("该单位尚未提交科普活动")
                else:
                    st.info("该单位尚未提交科普活动")
            
            # 技能竞赛
            with tabs[3]:
                if '技能竞赛' in unit_data:
                    comps = unit_data['技能竞赛'].get('技能竞赛', [])
                    if comps:
                        for idx, comp in enumerate(comps, 1):
                            with st.expander(f"{idx}. {comp['竞赛名称']} ({comp['日期']})"):
                                st.write(f"**简介：** {comp['竞赛简介']}")
                                st.write(f"**图片：** {len(comp['图片'])}张")
                    else:
                        st.info("该单位尚未提交技能竞赛")
                else:
                    st.info("该单位尚未提交技能竞赛")
            
            # 获奖情况
            with tabs[4]:
                if '获奖情况' in unit_data:
                    awards = unit_data['获奖情况'].get('获奖情况', [])
                    if awards:
                        for idx, award in enumerate(awards, 1):
                            with st.expander(f"{idx}. {award['奖项名称']} ({award['日期']})"):
                                st.write(f"**图片：** {len(award['图片'])}张")
                    else:
                        st.info("该单位尚未提交获奖情况")
                else:
                    st.info("该单位尚未提交获奖情况")
            
            # 科研立项
            with tabs[5]:
                if '科研立项' in unit_data:
                    projects = unit_data['科研立项'].get('科研立项', [])
                    if projects:
                        df = pd.DataFrame(projects)
                        st.dataframe(df, use_container_width=True)
                    else:
                        st.info("该单位尚未提交科研立项")
                else:
                    st.info("该单位尚未提交科研立项")
            
            # 论文发表
            with tabs[6]:
                if '论文发表' in unit_data:
                    pubs = unit_data['论文发表'].get('论文发表', [])
                    if pubs:
                        df = pd.DataFrame(pubs)
                        st.dataframe(df, use_container_width=True)
                    else:
                        st.info("该单位尚未提交论文发表")
                else:
                    st.info("该单位尚未提交论文发表")
    
    # ========== 分类汇总 ==========
    elif view_mode == "分类汇总":
        st.header("📑 分类数据汇总")
        
        category = st.selectbox(
            "选择类别",
            ["科研立项", "论文发表", "学术活动", "科普活动", "技能竞赛", "获奖情况"]
        )
        
        if category == "科研立项":
            all_projects = []
            for unit_name, unit_data in all_data.items():
                if '科研立项' in unit_data:
                    projects = unit_data['科研立项'].get('科研立项', [])
                    for proj in projects:
                        proj_copy = proj.copy()
                        proj_copy['单位名称'] = unit_name
                        all_projects.append(proj_copy)
            
            if all_projects:
                df = pd.DataFrame(all_projects)
                cols = ['单位名称'] + [col for col in df.columns if col != '单位名称']
                df = df[cols]
                st.dataframe(df, use_container_width=True)
                st.info(f"共 {len(all_projects)} 条记录")
            else:
                st.info("暂无数据")
        
        elif category == "论文发表":
            all_pubs = []
            for unit_name, unit_data in all_data.items():
                if '论文发表' in unit_data:
                    pubs = unit_data['论文发表'].get('论文发表', [])
                    for pub in pubs:
                        pub_copy = pub.copy()
                        pub_copy['单位名称'] = unit_name
                        all_pubs.append(pub_copy)
            
            if all_pubs:
                df = pd.DataFrame(all_pubs)
                cols = ['单位名称'] + [col for col in df.columns if col != '单位名称']
                df = df[cols]
                st.dataframe(df, use_container_width=True)
                st.info(f"共 {len(all_pubs)} 条记录")
            else:
                st.info("暂无数据")
        
        elif category in ["学术活动", "科普活动", "技能竞赛", "获奖情况"]:
            all_items = []
            for unit_name, unit_data in all_data.items():
                if category in unit_data:
                    items = unit_data[category].get(category, [])
                    for item in items:
                        item_summary = {
                            '单位名称': unit_name,
                            '日期': item['日期']
                        }
                        if category == "获奖情况":
                            item_summary['奖项名称'] = item['奖项名称']
                        elif category == "技能竞赛":
                            item_summary['竞赛名称'] = item['竞赛名称']
                            item_summary['竞赛简介'] = item['竞赛简介']
                        else:
                            item_summary['活动名称'] = item['活动名称']
                            item_summary['活动简介'] = item['活动简介']
                        
                        item_summary['图片数量'] = len(item['图片'])
                        all_items.append(item_summary)
            
            if all_items:
                df = pd.DataFrame(all_items)
                st.dataframe(df, use_container_width=True)
                st.info(f"共 {len(all_items)} 条记录")
            else:
                st.info("暂无数据")
    
    # 导出功能
    st.markdown("---")
    st.header("📥 数据导出")
    
    if st.button("生成完整Excel汇总表"):
        try:
            excel_file = export_all_to_excel(all_data)
            st.download_button(
                label="📥 下载Excel汇总表",
                data=excel_file,
                file_name=f"揭阳市临床药学分会_数据汇总_{datetime.now().strftime('%Y%m%d')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
            st.success("✅ Excel文件生成成功！")
        except Exception as e:
            st.error(f"生成Excel时出错：{str(e)}")

if __name__ == "__main__":
    main()
