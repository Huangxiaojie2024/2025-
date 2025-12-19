# 在管理后台的 "按单位查看" -> "获奖情况" 标签页中
# 将原来的代码替换为：

# 获奖情况
with tabs[4]:
    awards = get_unit_data("awards", selected_unit)
    if awards:
        for idx, award in enumerate(awards, 1):
            with st.expander(f"{idx}. {award['award_name']} ({award['award_date']})"):
                st.write(f"**颁奖单位：** {award.get('award_organization', '未填写')}")
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

# 在 "分类汇总" -> "获奖情况" 中也要添加颁奖单位显示
# 在相应位置添加：
if category == "🥇 获奖情况":
    title = f"{idx}. {unit} - {item['award_name']} ({item['award_date']})"
    with st.expander(title):
        st.write(f"**颁奖单位：** {item.get('award_organization', '未填写')}")
        # 图片显示代码...

# 在 Excel 导出部分也要添加颁奖单位字段
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
            '颁奖单位': award.get('award_organization', '未填写'),
            '图片链接': '\n'.join(image_urls) if image_urls else '无'
        })
    pd.DataFrame(df_data).to_excel(writer, sheet_name='获奖情况', index=False)
