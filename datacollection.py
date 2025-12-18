import streamlit as st
import pandas as pd
import json
from datetime import datetime
from supabase import create_client, Client
import io

st.set_page_config(
    page_title="揭阳市临床药学分会 - 管理员后台",
    page_icon="📊",
    layout="wide"
)

# ==================== Supabase配置 ====================
try:
    SUPABASE_URL = st.secrets["SUPABASE_URL"]
    SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
    ADMIN_PASSWORD = st.secrets.get("ADMIN_PASSWORD", "admin123")
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
except Exception as e:
    st.error("⚠️ 数据库配置错误，请联系管理员")
    st.stop()

# ==================== 身份验证 ====================
def check_password():
    """验证管理员密码"""
    def password_entered():
        if st.session_state["password"] == ADMIN_PASSWORD:
            st.session_state["password_correct"] = True
            del st.session_state["password"]
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        st.markdown("## 🔐 管理员登录")
        st.text_input(
            "请输入管理员密码", 
            type="password", 
            on_change=password_entered, 
            key="password"
        )
        return False
    elif not st.session_state["password_correct"]:
        st.markdown("## 🔐 管理员登录")
        st.text_input(
            "请输入管理员密码", 
            type="password", 
            on_change=password_entered, 
            key="password"
        )
        st.error("❌ 密码错误")
        return False
    else:
        return True

# ==================== 数据库操作函数 ====================
def get_all_data(table_name):
    """获取所有数据"""
    try:
        result = supabase.table(table_name).select("*").execute()
        return result.data
    except Exception as e:
        st.error(f"读取{table_name}数据失败: {str(e)}")
        return []

def get_unit_data(table_name, unit_name):
    """获取单个单位的数据"""
    try:
        result = supabase.table(table_name).select("*").eq("unit_name", unit_name).execute()
        return result.data
    except Exception as e:
        st.error(f"读取数据失败: {str(e)}")
        return []

# ==================== 主程序 ====================
def main():
    # 验证密码
    if not check_password():
        return
    
    st.title("📊 揭阳市临床药学分会数据管理后台")
    
    # 添加登出按钮
    if st.sidebar.button("🚪 退出登录"):
        st.session_state["password_correct"] = False
        st.rerun()
    
    st.markdown("---")
    
    # 获取所有单位列表
    work_summary_data = get_all_data("work_summary")
    all_units = list(set([item['unit_name'] for item in work_summary_data]))
    
    # 如果没有数据，尝试从其他表获取单位列表
    if not all_units:
        for table in ["academic_activities", "popular_activities", "competitions", "awards", "research_projects", "publications"]:
            data = get_all_data(table)
            if data:
                all_units.extend([item['unit_name'] for item in data])
        all_units = list(set(all_units))
    
    if not all_units:
        st.warning("⚠️ 暂无数据，请等待各单位提交")
        return
    
    # 侧边栏选择
    st.sidebar.header("📋 数据筛选")
    view_mode = st.sidebar.radio(
        "查看模式",
        ["📈 概览统计", "🏥 按单位查看", "📑 分类汇总", "📥 数据导出"]
    )
    
    # ========== 概览统计 ==========
    if view_mode == "📈 概览统计":
        st.header("📈 数据概览")
        
        # 统计信息
        col1, col2, col3, col4 = st.columns(4)
        
        academic_data = get_all_data("academic_activities")
        popular_data = get_all_data("popular_activities")
        comp_data = get_all_data("competitions")
        award_data = get_all_data("awards")
        
        with col1:
            st.metric("提交单位数", len(all_units))
        with col2:
            st.metric("学术活动总数", len(academic_data))
        with col3:
            st.metric("科普活动总数", len(popular_data))
        with col4:
            st.metric("技能竞赛总数", len(comp_data))
        
        col1, col2, col3 = st.columns(3)
        
        project_data = get_all_data("research_projects")
        pub_data = get_all_data("publications")
        
        with col1:
            st.metric("获奖总数", len(award_data))
        with col2:
            st.metric("科研立项总数", len(project_data))
        with col3:
            st.metric("论文发表总数", len(pub_data))
        
        st.markdown("---")
        
        # 提交情况表
        st.subheader("各单位提交情况")
        submit_data = []
        
        for unit in all_units:
            row = {
                '单位名称': unit,
                '年度总结': '✓' if any(item['unit_name'] == unit for item in work_summary_data) else '✗',
                '学术活动': len([item for item in academic_data if item['unit_name'] == unit]),
                '科普活动': len([item for item in popular_data if item['unit_name'] == unit]),
                '技能竞赛': len([item for item in comp_data if item['unit_name'] == unit]),
                '获奖情况': len([item for item in award_data if item['unit_name'] == unit]),
                '科研立项': len([item for item in project_data if item['unit_name'] == unit]),
                '论文发表': len([item for item in pub_data if item['unit_name'] == unit])
            }
            
            # 获取最后更新时间
            unit_summary = [item for item in work_summary_data if item['unit_name'] == unit]
            if unit_summary:
                row['最后更新'] = unit_summary[0].get('updated_at', '未知')[:19]
            else:
                row['最后更新'] = '未提交'
            
            submit_data.append(row)
        
        df_submit = pd.DataFrame(submit_data)
        st.dataframe(df_submit, use_container_width=True, hide_index=True)
    
    # ========== 按单位查看 ==========
    elif view_mode == "🏥 按单位查看":
        st.header("🏥 按单位查看数据")
        
        selected_unit = st.selectbox("选择单位", sorted(all_units))
        
        if selected_unit:
            tabs = st.tabs([
                "📄 年度总结",
                "🎓 学术活动",
                "📢 科普活动",
                "🏆 技能竞赛",
                "🥇 获奖情况",
                "🔬 科研立项",
                "📚 论文发表"
            ])
            
            # 年度总结
            with tabs[0]:
                summary_data = get_unit_data("work_summary", selected_unit)
                if summary_data:
                    info = summary_data[0]
                    st.write(f"**联系人：** {info.get('contact_person', '未填写')}")
                    st.write(f"**联系电话：** {info.get('contact_phone', '未填写')}")
                    st.write(f"**最后更新：** {info.get('updated_at', '未知')[:19]}")
                    
                    if info.get('summary_url'):
                        st.markdown(f"**年度总结与计划：** [📄 下载文档]({info['summary_url']})")
                    else:
                        st.info("未上传年度总结与计划")
                else:
                    st.info("该单位尚未提交年度总结与计划")
            
            # 学术活动
            with tabs[1]:
                academic = get_unit_data("academic_activities", selected_unit)
                if academic:
                    for idx, act in enumerate(academic, 1):
                        with st.expander(f"{idx}. {act['activity_name']} ({act['activity_date']})"):
                            st.write(f"**简介：** {act['description']}")
                            image_urls = json.loads(act.get('image_urls', '[]'))
                            if image_urls:
                                st.write(f"**图片：** {len(image_urls)}张")
                                cols = st.columns(min(len(image_urls), 3))
                                for img_idx, img_url in enumerate(image_urls):
                                    with cols[img_idx % 3]:
                                        try:
                                            st.image(img_url, use_container_width=True)
                                        except:
                                            st.markdown(f"[🖼️ 查看图片]({img_url})")
                else:
                    st.info("该单位尚未提交学术活动")
            
            # 科普活动
            with tabs[2]:
                popular = get_unit_data("popular_activities", selected_unit)
                if popular:
                    for idx, act in enumerate(popular, 1):
                        with st.expander(f"{idx}. {act['activity_name']} ({act['activity_date']})"):
                            st.write(f"**简介：** {act['description']}")
                            image_urls = json.loads(act.get('image_urls', '[]'))
                            if image_urls:
                                st.write(f"**图片：** {len(image_urls)}张")
                                cols = st.columns(min(len(image_urls), 3))
                                for img_idx, img_url in enumerate(image_urls):
                                    with cols[img_idx % 3]:
                                        try:
                                            st.image(img_url, use_container_width=True)
                                        except:
                                            st.markdown(f"[🖼️ 查看图片]({img_url})")
                else:
                    st.info("该单位尚未提交科普活动")
            
            # 技能竞赛
            with tabs[3]:
                comps = get_unit_data("competitions", selected_unit)
                if comps:
                    for idx, comp in enumerate(comps, 1):
                        with st.expander(f"{idx}. {comp['competition_name']} ({comp['competition_date']})"):
                            st.write(f"**简介：** {comp['description']}")
                            image_urls = json.loads(comp.get('image_urls', '[]'))
                            if image_urls:
                                st.write(f"**图片：** {len(image_urls)}张")
                                cols = st.columns(min(len(image_urls), 3))
                                for img_idx, img_url in enumerate(image_urls):
                                    with cols[img_idx % 3]:
                                        try:
                                            st.image(img_url, use_container_width=True)
                                        except:
                                            st.markdown(f"[🖼️ 查看图片]({img_url})")
                else:
                    st.info("该单位尚未提交技能竞赛")
            
            # 获奖情况
            with tabs[4]:
                awards = get_unit_data("awards", selected_unit)
                if awards:
                    for idx, award in enumerate(awards, 1):
                        with st.expander(f"{idx}. {award['award_name']} ({award['award_date']})"):
                            image_urls = json.loads(award.get('image_urls', '[]'))
                            if image_urls:
                                st.write(f"**图片：** {len(image_urls)}张")
                                cols = st.columns(min(len(image_urls), 3))
                                for img_idx, img_url in enumerate(image_urls):
                                    with cols[img_idx % 3]:
                                        try:
                                            st.image(img_url, use_container_width=True)
                                        except:
                                            st.markdown(f"[🖼️ 查看图片]({img_url})")
                else:
                    st.info("该单位尚未提交获奖情况")
            
            # 科研立项
            with tabs[5]:
                projects = get_unit_data("research_projects", selected_unit)
                if projects:
                    df_data = []
                    for proj in projects:
                        df_data.append({
                            '项目负责人': proj['project_leader'],
                            '项目名称': proj['project_name'],
                            '立项单位': proj['project_unit'],
                            '基金名称': proj['fund_name'],
                            '编号': proj['fund_number'],
                            '资助金额（万元）': proj['fund_amount'],
                            '立项时间': proj['project_date']
                        })
                    df = pd.DataFrame(df_data)
                    st.dataframe(df, use_container_width=True, hide_index=True)
                else:
                    st.info("该单位尚未提交科研立项")
            
            # 论文发表
            with tabs[6]:
                pubs = get_unit_data("publications", selected_unit)
                if pubs:
                    df_data = []
                    for pub in pubs:
                        df_data.append({
                            '类型': pub['publication_type'],
                            '题目': pub['title'],
                            '刊物名称': pub['journal'],
                            '作者': pub['author'],
                            '刊物等级': pub['level'],
                            '发表时间': pub['publication_date']
                        })
                    df = pd.DataFrame(df_data)
                    st.dataframe(df, use_container_width=True, hide_index=True)
                else:
                    st.info("该单位尚未提交论文发表")
    
    # ========== 分类汇总 ==========
    elif view_mode == "📑 分类汇总":
        st.header("📑 分类数据汇总")
        
        category = st.selectbox(
            "选择类别",
            ["🔬 科研立项", "📚 论文发表", "🎓 学术活动", "📢 科普活动", "🏆 技能竞赛", "🥇 获奖情况"]
        )
        
        if category == "🔬 科研立项":
            projects = get_all_data("research_projects")
            if projects:
                df_data = []
                for proj in projects:
                    df_data.append({
                        '单位名称': proj['unit_name'],
                        '项目负责人': proj['project_leader'],
                        '项目名称': proj['project_name'],
                        '立项单位': proj['project_unit'],
                        '基金名称': proj['fund_name'],
                        '编号': proj['fund_number'],
                        '资助金额（万元）': proj['fund_amount'],
                        '立项时间': proj['project_date']
                    })
                df = pd.DataFrame(df_data)
                st.dataframe(df, use_container_width=True, hide_index=True)
                st.info(f"共 {len(projects)} 条记录")
            else:
                st.info("暂无数据")
        
        elif category == "📚 论文发表":
            pubs = get_all_data("publications")
            if pubs:
                df_data = []
                for pub in pubs:
                    df_data.append({
                        '单位名称': pub['unit_name'],
                        '类型': pub['publication_type'],
                        '题目': pub['title'],
                        '刊物名称': pub['journal'],
                        '作者': pub['author'],
                        '刊物等级': pub['level'],
                        '发表时间': pub['publication_date']
                    })
                df = pd.DataFrame(df_data)
                st.dataframe(df, use_container_width=True, hide_index=True)
                st.info(f"共 {len(pubs)} 条记录")
            else:
                st.info("暂无数据")
        
        elif category in ["🎓 学术活动", "📢 科普活动", "🏆 技能竞赛", "🥇 获奖情况"]:
            table_map = {
                "🎓 学术活动": "academic_activities",
                "📢 科普活动": "popular_activities",
                "🏆 技能竞赛": "competitions",
                "🥇 获奖情况": "awards"
            }
            
            data = get_all_data(table_map[category])
            if data:
                for idx, item in enumerate(data, 1):
                    unit = item['unit_name']
                    
                    if category == "🥇 获奖情况":
                        title = f"{idx}. {unit} - {item['award_name']} ({item['award_date']})"
                    elif category == "🏆 技能竞赛":
                        title = f"{idx}. {unit} - {item['competition_name']} ({item['competition_date']})"
                        description = item['description']
                    else:
                        title = f"{idx}. {unit} - {item['activity_name']} ({item['activity_date']})"
                        description = item['description']
                    
                    with st.expander(title):
                        if category != "🥇 获奖情况":
                            st.write(f"**简介：** {description}")
                        
                        image_urls = json.loads(item.get('image_urls', '[]'))
                        if image_urls:
                            st.write(f"**图片：** {len(image_urls)}张")
                            cols = st.columns(min(len(image_urls), 3))
                            for img_idx, img_url in enumerate(image_urls):
                                with cols[img_idx % 3]:
                                    try:
                                        st.image(img_url, use_container_width=True)
                                    except:
                                        st.markdown(f"[🖼️ 查看图片]({img_url})")
                
                st.info(f"共 {len(data)} 条记录")
            else:
                st.info("暂无数据")
    
    # ========== 数据导出 ==========
    elif view_mode == "📥 数据导出":
        st.header("📥 数据导出")
        
        st.info("💡 导出的Excel将包含所有数据和图片链接")
        
        if st.button("📊 生成完整Excel汇总表（含图片链接）", type="primary"):
            with st.spinner("正在生成Excel文件..."):
                try:
                    output = io.BytesIO()
                    with pd.ExcelWriter(output, engine='openpyxl') as writer:
                        # 科研立项
                        projects = get_all_data("research_projects")
                        if projects:
                            df_data = []
                            for proj in projects:
                                df_data.append({
                                    '单位名称': proj['unit_name'],
                                    '项目负责人': proj['project_leader'],
                                    '项目名称': proj['project_name'],
                                    '立项单位': proj['project_unit'],
                                    '基金名称': proj['fund_name'],
                                    '编号': proj['fund_number'],
                                    '资助金额（万元）': proj['fund_amount'],
                                    '立项时间': proj['project_date']
                                })
                            pd.DataFrame(df_data).to_excel(writer, sheet_name='科研立项', index=False)
                        
                        # 论文发表
                        pubs = get_all_data("publications")
                        if pubs:
                            df_data = []
                            for pub in pubs:
                                df_data.append({
                                    '单位名称': pub['unit_name'],
                                    '类型': pub['publication_type'],
                                    '题目': pub['title'],
                                    '刊物名称': pub['journal'],
                                    'CN号/出版社': pub['cn_number'],
                                    '主管部门': pub['department'],
                                    '卷期': pub['issue'],
                                    '页码': pub['pages'],
                                    '作者': pub['author'],
                                    '刊物等级': pub['level'],
                                    '发表时间': pub['publication_date']
                                })
                            pd.DataFrame(df_data).to_excel(writer, sheet_name='论文发表', index=False)
                        
                        # 学术活动（带图片链接）
                        academic = get_all_data("academic_activities")
                        if academic:
                            df_data = []
                            for act in academic:
                                image_urls = json.loads(act.get('image_urls', '[]'))
                                df_data.append({
                                    '单位名称': act['unit_name'],
                                    '日期': act['activity_date'],
                                    '活动名称': act['activity_name'],
                                    '活动简介': act['description'],
                                    '图片链接': '\n'.join(image_urls) if image_urls else '无'
                                })
                            pd.DataFrame(df_data).to_excel(writer, sheet_name='学术活动', index=False)
                        
                        # 科普活动（带图片链接）
                        popular = get_all_data("popular_activities")
                        if popular:
                            df_data = []
                            for act in popular:
                                image_urls = json.loads(act.get('image_urls', '[]'))
                                df_data.append({
                                    '单位名称': act['unit_name'],
                                    '日期': act['activity_date'],
                                    '活动名称': act['activity_name'],
                                    '活动简介': act['description'],
                                    '图片链接': '\n'.join(image_urls) if image_urls else '无'
                                })
                            pd.DataFrame(df_data).to_excel(writer, sheet_name='科普活动', index=False)
                        
                        # 技能竞赛（带图片链接）
                        comps = get_all_data("competitions")
                        if comps:
                            df_data = []
                            for comp in comps:
                                image_urls = json.loads(comp.get('image_urls', '[]'))
                                df_data.append({
                                    '单位名称': comp['unit_name'],
                                    '日期': comp['competition_date'],
                                    '竞赛名称': comp['competition_name'],
                                    '竞赛简介': comp['description'],
                                    '图片链接': '\n'.join(image_urls) if image_urls else '无'
                                })
                            pd.DataFrame(df_data).to_excel(writer, sheet_name='技能竞赛', index=False)
                        
                        # 获奖情况（带图片链接）
                        awards = get_all_data("awards")
                        if awards:
                            df_data = []
                            for award in awards:
                                image_urls = json.loads(award.get('image_urls', '[]'))
                                df_data.append({
                                    '单位名称': award['unit_name'],
                                    '日期': award['award_date'],
                                    '奖项名称': award['award_name'],
                                    '图片链接': '\n'.join(image_urls) if image_urls else '无'
                                })
                            pd.DataFrame(df_data).to_excel(writer, sheet_name='获奖情况', index=False)
                        
                        # 提交情况统计
                        work_summary = get_all_data("work_summary")
                        submit_data = []
                        for unit in all_units:
                            submit_data.append({
                                '单位名称': unit,
                                '年度总结': '✓' if any(item['unit_name'] == unit for item in work_summary) else '✗',
                                '学术活动': len([item for item in academic if item['unit_name'] == unit]),
                                '科普活动': len([item for item in popular if item['unit_name'] == unit]),
                                '技能竞赛': len([item for item in comps if item['unit_name'] == unit]),
                                '获奖情况': len([item for item in awards if item['unit_name'] == unit]),
                                '科研立项': len([item for item in projects if item['unit_name'] == unit]),
                                '论文发表': len([item for item in pubs if item['unit_name'] == unit])
                            })
                        pd.DataFrame(submit_data).to_excel(writer, sheet_name='提交情况统计', index=False)
                    
                    output.seek(0)
                    st.download_button(
                        label="📥 下载Excel汇总表",
                        data=output,
                        file_name=f"揭阳市临床药学分会_数据汇总_{datetime.now().strftime('%Y%m%d')}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
                    st.success("✅ Excel文件生成成功！图片链接已包含在各个工作表中")
                except Exception as e:
                    st.error(f"生成Excel时出错：{str(e)}")

if __name__ == "__main__":
    main()
