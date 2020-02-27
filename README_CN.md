
# NCMusic

**使用Python进行开发的,涵盖移动端的跨平台音乐播放器**

NCMusic是一个模仿网易云音乐ui设计的音乐播放器,并尽力与网易云官网数据进行同步,使用户可以在保证不损失已有歌单的情况下使用该软件.


##安装使用: 
- pc端: 克隆该仓库,按需安装依赖后运行main.py即可
- 安卓: 直接进入bin文件夹下载.apk文件安装即可

##说明:
目前该项目仍处于开发阶段, 已实现的功能有:
- 使用手机号登录并同步用户昵称,头像,喜欢的音乐
- 网易云原生每日歌单推荐
- 原生每日音乐单曲推荐
- 添加喜欢/删除喜欢的歌曲
- 边听边存,所有歌曲播放过后会自动缓存,再次播放时自动从本地加载
- 夜间模式
- 个性换肤

目前基本开发完的界面有:
- 登录界面 ![login](img/login.png"login")
- 用户主界面![markdown](src/login_logo.png")
- 左侧工具栏
- 歌单推荐页

已进行开发但不完善的界面(具有刚需功能但界面未完成美化):
- 歌曲详情界面(歌词界面)
- 搜索界面
- 歌单详情页

未开始或开发甚少的界面:
- 视频播放界面
- "朋友" "电台" "直播" "视频" 界面

> 对于大多未开发界面的说明: 未找到相关api并且大部分用户对其并无太大需求.


##大致界面展示:
###pc端:

- 登录: ![login](img/login_0.png"login")
![login](img/login_1.png"login")
- 主界面: ![main](img/main_0.png"main")
- 侧栏: ![sidebar](img/main_0.png"siderbar")
- 推荐歌单: ![rec_musiclist](img/rec_musiclist.png"recmmend_musiclist")
![rec_musiclist](img/rec_musiclist_1.png"recmmend_musiclist")
- 歌曲详情页: ![music_detail](img/music_detail.png"music_detail")
![music_detail](img/music_detail_1.png"music_detail")
- 歌单详情页: ![musiclist_detail](img/music_list.png"musiclist_detail")
- 搜索界面: ![search](img/search.png"search")
- 夜间模式: ![night](img/night_rec_musiclist.png"night_rec_musiclist")
![night](img/night_main.png"night_main")

###安卓端:
稍后更新图
##开源许可:
- 本项目根据Apache-2.0协议发布, 请参考许可文件

