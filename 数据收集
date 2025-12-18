import streamlit as st
import pandas as pd
from datetime import datetime
import os
import json
from pathlib import Path
import zipfile
import io

# 设置页面配置
st.set_page_config(
    page_title="揭阳市医学会临床药学分会数据收集系统",
    page_icon="💊",
    layout="wide"
)

# 创建数据存储目录
DATA_DIR = Path("data_submissions")
DATA_DIR.mkdir(exist_ok=True)

def save_uploaded_file(uploaded_file, unit_name, category, file_index=None):
    """保存上传的文件"""
    unit_dir = DATA_DIR / unit_name / category
    unit_dir.mkdir(parents=True, exist_ok=True)
    
    if file_index is not None:
        filename = f"{file_index}_{uploaded_file.name}"
    else:
        filename = uploaded_file.name
    
    file_path = unit_dir / filename
    with open(file_path, "wb") as f:
        f.write(uploaded_file.getbuffer())
    
    return str(file_path)

def save_data_to_json(data, unit_name, category):
    """保存数据到JSON文件"""
    unit_dir = DATA_DIR / unit_name
    unit_dir.mkdir(parents=True, exist_ok=True)
    
    json_file = unit_dir / f"{category}.json"
    with open(json_file, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def main():
    st.title("💊 揭阳市医学会临床药学分会数据收集系统")
    st.markdown("---")
    
    # 单位信息
    st.header("📋 单位信息")
    unit_name = st.text_input("请输入单位名称", placeholder="例如：揭阳市人民医院")
    contact_person = st.text_input("联系人", placeholder="请输入联系人姓名")
    contact_phone = st.text_input("联系电话", placeholder="请输入联系电话")
    
    if not unit_name:
        st.warning("请先填写单位名称后再继续填报")
        return
    
    st.markdown("---")
    
    # 创建标签页
    tabs = st.tabs([
        "📄 工作总结与计划",
        "🎓 学术活动",
        "📢 科普活动",
        "🏆 技能竞赛",
        "🥇 获奖情况",
        "🔬 科研立项",
        "📚 论文发表",
        "📦 数据导出"
    ])
    
    # ========== 工作总结与计划 ==========
    with tabs[0]:
        st.subheader("工作总结与计划")
        
        col1, col2 = st.columns(2)
        with col1:
            summary_file = st.file_uploader(
                "上传2025年工作总结（Word文档）",
                type=['doc', 'docx'],
                key="summary"
            )
        
        with col2:
            plan_file = st.file_uploader(
                "上传2026年工作计划（Word文档）",
                type=['doc', 'docx'],
                key="plan"
            )
        
        if st.button("保存工作总结与计划", key="save_summary_plan"):
            if summary_file or plan_file:
                saved_files = {}
                if summary_file:
                    path = save_uploaded_file(summary_file, unit_name, "工作总结与计划")
                    saved_files["2025年工作总结"] = path
                if plan_file:
                    path = save_uploaded_file(plan_file, unit_name, "工作总结与计划")
                    saved_files["2026年工作计划"] = path
                
                save_data_to_json({
                    "单位名称": unit_name,
                    "联系人": contact_person,
                    "联系电话": contact_phone,
                    "文件": saved_files,
                    "提交时间": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }, unit_name, "工作总结与计划_info")
                
                st.success("✅ 保存成功！")
            else:
                st.warning("请至少上传一个文件")
    
    # ========== 学术活动 ==========
    with tabs[1]:
        st.subheader("学术活动登记")
        
        if 'academic_activities' not in st.session_state:
            st.session_state.academic_activities = []
        
        with st.expander("➕ 添加新的学术活动", expanded=True):
            col1, col2 = st.columns(2)
            with col1:
                activity_date = st.date_input("活动日期", key="academic_date")
            with col2:
                activity_name = st.text_input("活动名称", key="academic_name")
            
            activity_desc = st.text_area("活动简介", key="academic_desc", height=100)
            
            activity_images = st.file_uploader(
                "上传活动图片（最多3张）",
                type=['jpg', 'jpeg', 'png'],
                accept_multiple_files=True,
                key="academic_images"
            )
            
            if st.button("添加学术活动", key="add_academic"):
                if activity_name and activity_desc:
                    if activity_images and len(activity_images) > 3:
                        st.error("最多只能上传3张图片")
                    else:
                        # 保存图片
                        image_paths = []
                        for idx, img in enumerate(activity_images):
                            path = save_uploaded_file(
                                img, 
                                unit_name, 
                                f"学术活动/{activity_name}", 
                                idx
                            )
                            image_paths.append(path)
                        
                        activity_data = {
                            "日期": str(activity_date),
                            "活动名称": activity_name,
                            "活动简介": activity_desc,
                            "图片": image_paths
                        }
                        st.session_state.academic_activities.append(activity_data)
                        st.success(f"✅ 已添加学术活动：{activity_name}")
                        st.rerun()
                else:
                    st.error("请填写活动名称和简介")
        
        # 显示已添加的活动
        if st.session_state.academic_activities:
            st.markdown("### 已添加的学术活动")
            for idx, activity in enumerate(st.session_state.academic_activities):
                with st.expander(f"{activity['活动名称']} - {activity['日期']}"):
                    st.write(f"**简介：** {activity['活动简介']}")
                    st.write(f"**图片数量：** {len(activity['图片'])}张")
                    if st.button(f"删除", key=f"del_academic_{idx}"):
                        st.session_state.academic_activities.pop(idx)
                        st.rerun()
        
        if st.button("保存所有学术活动", key="save_academic"):
            if st.session_state.academic_activities:
                save_data_to_json({
                    "单位名称": unit_name,
                    "学术活动": st.session_state.academic_activities,
                    "提交时间": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }, unit_name, "学术活动")
                st.success(f"✅ 已保存{len(st.session_state.academic_activities)}条学术活动记录！")
    
    # ========== 科普活动 ==========
    with tabs[2]:
        st.subheader("科普活动登记")
        
        if 'popular_activities' not in st.session_state:
            st.session_state.popular_activities = []
        
        with st.expander("➕ 添加新的科普活动", expanded=True):
            col1, col2 = st.columns(2)
            with col1:
                pop_date = st.date_input("活动日期", key="pop_date")
            with col2:
                pop_name = st.text_input("活动名称", key="pop_name")
            
            pop_desc = st.text_area("活动简介", key="pop_desc", height=100)
            
            pop_images = st.file_uploader(
                "上传活动图片（最多3张）",
                type=['jpg', 'jpeg', 'png'],
                accept_multiple_files=True,
                key="pop_images"
            )
            
            if st.button("添加科普活动", key="add_pop"):
                if pop_name and pop_desc:
                    if pop_images and len(pop_images) > 3:
                        st.error("最多只能上传3张图片")
                    else:
                        image_paths = []
                        for idx, img in enumerate(pop_images):
                            path = save_uploaded_file(
                                img, 
                                unit_name, 
                                f"科普活动/{pop_name}", 
                                idx
                            )
                            image_paths.append(path)
                        
                        activity_data = {
                            "日期": str(pop_date),
                            "活动名称": pop_name,
                            "活动简介": pop_desc,
                            "图片": image_paths
                        }
                        st.session_state.popular_activities.append(activity_data)
                        st.success(f"✅ 已添加科普活动：{pop_name}")
                        st.rerun()
                else:
                    st.error("请填写活动名称和简介")
        
        if st.session_state.popular_activities:
            st.markdown("### 已添加的科普活动")
            for idx, activity in enumerate(st.session_state.popular_activities):
                with st.expander(f"{activity['活动名称']} - {activity['日期']}"):
                    st.write(f"**简介：** {activity['活动简介']}")
                    st.write(f"**图片数量：** {len(activity['图片'])}张")
                    if st.button(f"删除", key=f"del_pop_{idx}"):
                        st.session_state.popular_activities.pop(idx)
                        st.rerun()
        
        if st.button("保存所有科普活动", key="save_pop"):
            if st.session_state.popular_activities:
                save_data_to_json({
                    "单位名称": unit_name,
                    "科普活动": st.session_state.popular_activities,
                    "提交时间": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }, unit_name, "科普活动")
                st.success(f"✅ 已保存{len(st.session_state.popular_activities)}条科普活动记录！")
    
    # ========== 技能竞赛 ==========
    with tabs[3]:
        st.subheader("技能竞赛登记")
        
        if 'competitions' not in st.session_state:
            st.session_state.competitions = []
        
        with st.expander("➕ 添加新的技能竞赛", expanded=True):
            col1, col2 = st.columns(2)
            with col1:
                comp_date = st.date_input("竞赛日期", key="comp_date")
            with col2:
                comp_name = st.text_input("竞赛名称", key="comp_name")
            
            comp_desc = st.text_area("竞赛简介", key="comp_desc", height=100)
            
            comp_images = st.file_uploader(
                "上传竞赛图片",
                type=['jpg', 'jpeg', 'png'],
                accept_multiple_files=True,
                key="comp_images"
            )
            
            if st.button("添加技能竞赛", key="add_comp"):
                if comp_name and comp_desc:
                    image_paths = []
                    for idx, img in enumerate(comp_images):
                        path = save_uploaded_file(
                            img, 
                            unit_name, 
                            f"技能竞赛/{comp_name}", 
                            idx
                        )
                        image_paths.append(path)
                    
                    comp_data = {
                        "日期": str(comp_date),
                        "竞赛名称": comp_name,
                        "竞赛简介": comp_desc,
                        "图片": image_paths
                    }
                    st.session_state.competitions.append(comp_data)
                    st.success(f"✅ 已添加技能竞赛：{comp_name}")
                    st.rerun()
                else:
                    st.error("请填写竞赛名称和简介")
        
        if st.session_state.competitions:
            st.markdown("### 已添加的技能竞赛")
            for idx, comp in enumerate(st.session_state.competitions):
                with st.expander(f"{comp['竞赛名称']} - {comp['日期']}"):
                    st.write(f"**简介：** {comp['竞赛简介']}")
                    st.write(f"**图片数量：** {len(comp['图片'])}张")
                    if st.button(f"删除", key=f"del_comp_{idx}"):
                        st.session_state.competitions.pop(idx)
                        st.rerun()
        
        if st.button("保存所有技能竞赛", key="save_comp"):
            if st.session_state.competitions:
                save_data_to_json({
                    "单位名称": unit_name,
                    "技能竞赛": st.session_state.competitions,
                    "提交时间": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }, unit_name, "技能竞赛")
                st.success(f"✅ 已保存{len(st.session_state.competitions)}条技能竞赛记录！")
    
    # ========== 获奖情况 ==========
    with tabs[4]:
        st.subheader("获奖情况登记")
        
        if 'awards' not in st.session_state:
            st.session_state.awards = []
        
        with st.expander("➕ 添加新的获奖记录", expanded=True):
            col1, col2 = st.columns(2)
            with col1:
                award_date = st.date_input("获奖日期", key="award_date")
            with col2:
                award_name = st.text_input("奖项名称", key="award_name")
            
            award_images = st.file_uploader(
                "上传获奖图片",
                type=['jpg', 'jpeg', 'png'],
                accept_multiple_files=True,
                key="award_images"
            )
            
            if st.button("添加获奖记录", key="add_award"):
                if award_name:
                    image_paths = []
                    for idx, img in enumerate(award_images):
                        path = save_uploaded_file(
                            img, 
                            unit_name, 
                            f"获奖/{award_name}", 
                            idx
                        )
                        image_paths.append(path)
                    
                    award_data = {
                        "日期": str(award_date),
                        "奖项名称": award_name,
                        "图片": image_paths
                    }
                    st.session_state.awards.append(award_data)
                    st.success(f"✅ 已添加获奖记录：{award_name}")
                    st.rerun()
                else:
                    st.error("请填写奖项名称")
        
        if st.session_state.awards:
            st.markdown("### 已添加的获奖记录")
            for idx, award in enumerate(st.session_state.awards):
                with st.expander(f"{award['奖项名称']} - {award['日期']}"):
                    st.write(f"**图片数量：** {len(award['图片'])}张")
                    if st.button(f"删除", key=f"del_award_{idx}"):
                        st.session_state.awards.pop(idx)
                        st.rerun()
        
        if st.button("保存所有获奖记录", key="save_award"):
            if st.session_state.awards:
                save_data_to_json({
                    "单位名称": unit_name,
                    "获奖情况": st.session_state.awards,
                    "提交时间": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }, unit_name, "获奖情况")
                st.success(f"✅ 已保存{len(st.session_state.awards)}条获奖记录！")
    
    # ========== 科研立项 ==========
    with tabs[5]:
        st.subheader("科研立项登记")
        
        if 'research_projects' not in st.session_state:
            st.session_state.research_projects = []
        
        with st.expander("➕ 添加新的科研立项", expanded=True):
            col1, col2 = st.columns(2)
            with col1:
                project_leader = st.text_input("项目负责人", key="proj_leader")
                project_name = st.text_input("项目名称", key="proj_name")
                project_unit = st.text_input("立项单位", key="proj_unit")
            
            with col2:
                fund_name = st.text_input("基金名称", key="fund_name")
                fund_number = st.text_input("编号", key="fund_number")
                fund_amount = st.number_input("资助金额（万元）", min_value=0.0, step=0.1, key="fund_amount")
            
            project_date = st.date_input("立项时间", key="proj_date")
            project_plan = st.text_area("计划", key="proj_plan", height=100)
            
            if st.button("添加科研立项", key="add_project"):
                if project_leader and project_name:
                    project_data = {
                        "项目负责人": project_leader,
                        "项目名称": project_name,
                        "立项单位": project_unit,
                        "计划": project_plan,
                        "基金名称": fund_name,
                        "编号": fund_number,
                        "资助金额（万元）": fund_amount,
                        "立项时间": str(project_date)
                    }
                    st.session_state.research_projects.append(project_data)
                    st.success(f"✅ 已添加科研立项：{project_name}")
                    st.rerun()
                else:
                    st.error("请至少填写项目负责人和项目名称")
        
        if st.session_state.research_projects:
            st.markdown("### 已添加的科研立项")
            df = pd.DataFrame(st.session_state.research_projects)
            st.dataframe(df, use_container_width=True)
            
            for idx in range(len(st.session_state.research_projects)):
                if st.button(f"删除第{idx+1}条", key=f"del_proj_{idx}"):
                    st.session_state.research_projects.pop(idx)
                    st.rerun()
        
        if st.button("保存所有科研立项", key="save_project"):
            if st.session_state.research_projects:
                save_data_to_json({
                    "单位名称": unit_name,
                    "科研立项": st.session_state.research_projects,
                    "提交时间": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }, unit_name, "科研立项")
                st.success(f"✅ 已保存{len(st.session_state.research_projects)}条科研立项记录！")
    
    # ========== 论文发表 ==========
    with tabs[6]:
        st.subheader("论文发表登记")
        
        if 'publications' not in st.session_state:
            st.session_state.publications = []
        
        with st.expander("➕ 添加新的论文发表", expanded=True):
            pub_type = st.selectbox(
                "类型",
                ["论文", "专著", "专利"],
                key="pub_type"
            )
            
            col1, col2 = st.columns(2)
            with col1:
                pub_title = st.text_input("论文/专著/专利题目", key="pub_title")
                pub_journal = st.text_input("刊物/专著名称", key="pub_journal")
                pub_cn = st.text_input("刊物CN号/出版社名称", key="pub_cn")
                pub_department = st.text_input("刊物主管部门", key="pub_dept")
            
            with col2:
                pub_issue = st.text_input("期刊、卷期", key="pub_issue")
                pub_pages = st.text_input("页码", key="pub_pages")
                pub_author = st.text_input("第一作者/通讯作者", key="pub_author")
                pub_level = st.selectbox(
                    "刊物等级",
                    ["SCI", "中文核心期刊", "科技核心", "省级期刊", "其他"],
                    key="pub_level"
                )
            
            pub_date = st.date_input("发表时间", key="pub_date")
            
            if st.button("添加论文发表", key="add_pub"):
                if pub_title and pub_author:
                    pub_data = {
                        "类型": pub_type,
                        "论文/专著/专利题目": pub_title,
                        "刊物/专著名称": pub_journal,
                        "刊物CN号/出版社名称": pub_cn,
                        "刊物主管部门": pub_department,
                        "期刊、卷期": pub_issue,
                        "页码": pub_pages,
                        "第一作者/通讯作者": pub_author,
                        "刊物等级": pub_level,
                        "发表时间": str(pub_date)
                    }
                    st.session_state.publications.append(pub_data)
                    st.success(f"✅ 已添加论文发表：{pub_title}")
                    st.rerun()
                else:
                    st.error("请至少填写题目和作者")
        
        if st.session_state.publications:
            st.markdown("### 已添加的论文发表")
            df = pd.DataFrame(st.session_state.publications)
            st.dataframe(df, use_container_width=True)
            
            for idx in range(len(st.session_state.publications)):
                if st.button(f"删除第{idx+1}条", key=f"del_pub_{idx}"):
                    st.session_state.publications.pop(idx)
                    st.rerun()
        
        if st.button("保存所有论文发表", key="save_pub"):
            if st.session_state.publications:
                save_data_to_json({
                    "单位名称": unit_name,
                    "论文发表": st.session_state.publications,
                    "提交时间": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }, unit_name, "论文发表")
                st.success(f"✅ 已保存{len(st.session_state.publications)}条论文发表记录！")
    
    # ========== 数据导出 ==========
    with tabs[7]:
        st.subheader("数据导出")
        
        st.info("📌 所有数据已自动保存到本地data_submissions文件夹中")
        
        # 生成Excel汇总表
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("生成Excel汇总表", key="export_excel"):
                try:
                    # 创建Excel文件
                    output = io.BytesIO()
                    with pd.ExcelWriter(output, engine='openpyxl') as writer:
                        # 科研立项
                        if st.session_state.get('research_projects'):
                            df_proj = pd.DataFrame(st.session_state.research_projects)
                            df_proj.insert(0, '单位名称', unit_name)
                            df_proj.to_excel(writer, sheet_name='科研立项', index=False)
                        
                        # 论文发表
                        if st.session_state.get('publications'):
                            df_pub = pd.DataFrame(st.session_state.publications)
                            df_pub.insert(0, '单位名称', unit_name)
                            df_pub.to_excel(writer, sheet_name='论文发表', index=False)
                        
                        # 学术活动
                        if st.session_state.get('academic_activities'):
                            activities = []
                            for act in st.session_state.academic_activities:
                                activities.append({
                                    '单位名称': unit_name,
                                    '日期': act['日期'],
                                    '活动名称': act['活动名称'],
                                    '活动简介': act['活动简介'],
                                    '图片数量': len(act['图片'])
                                })
                            df_acad = pd.DataFrame(activities)
                            df_acad.to_excel(writer, sheet_name='学术活动', index=False)
                        
                        # 科普活动
                        if st.session_state.get('popular_activities'):
                            activities = []
                            for act in st.session_state.popular_activities:
                                activities.append({
                                    '单位名称': unit_name,
                                    '日期': act['日期'],
                                    '活动名称': act['活动名称'],
                                    '活动简介': act['活动简介'],
                                    '图片数量': len(act['图片'])
                                })
                            df_pop = pd.DataFrame(activities)
                            df_pop.to_excel(writer, sheet_name='科普活动', index=False)
                        
                        # 技能竞赛
                        if st.session_state.get('competitions'):
                            comps = []
                            for comp in st.session_state.competitions:
                                comps.append({
                                    '单位名称': unit_name,
                                    '日期': comp['日期'],
                                    '竞赛名称': comp['竞赛名称'],
                                    '竞赛简介': comp['竞赛简介'],
                                    '图片数量': len(comp['图片'])
                                })
                            df_comp = pd.DataFrame(comps)
                            df_comp.to_excel(writer, sheet_name='技能竞赛', index=False)
                        
                        # 获奖情况
                        if st.session_state.get('awards'):
                            awards = []
                            for award in st.session_state.awards:
                                awards.append({
                                    '单位名称': unit_name,
                                    '日期': award['日期'],
                                    '奖项名称': award['奖项名称'],
                                    '图片数量': len(award['图片'])
                                })
                            df_award = pd.DataFrame(awards)
                            df_award.to_excel(writer, sheet_name='获奖情况', index=False)
                    
                    output.seek(0)
                    st.download_button(
                        label="📥 下载Excel汇总表",
                        data=output,
                        file_name=f"{unit_name}_数据汇总_{datetime.now().strftime('%Y%m%d')}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
                    st.success("✅ Excel汇总表生成成功！")
                except Exception as e:
                    st.error(f"生成Excel时出错：{str(e)}")
        
        with col2:
            st.markdown("### 数据存储位置")
            st.code(f"data_submissions/{unit_name}/")
            
        # 显示统计信息
        st.markdown("---")
        st.markdown("### 📊 数据统计")
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("学术活动", len(st.session_state.get('academic_activities', [])))
        with col2:
            st.metric("科普活动", len(st.session_state.get('popular_activities', [])))
        with col3:
            st.metric("技能竞赛", len(st.session_state.get('competitions', [])))
        with col4:
            st.metric("获奖情况", len(st.session_state.get('awards', [])))
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("科研立项", len(st.session_state.get('research_projects', [])))
        with col2:
            st.metric("论文发表", len(st.session_state.get('publications', [])))

if __name__ == "__main__":
    main()
