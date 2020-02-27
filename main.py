import sys
sys.path.append('./NEMbox')

import os, re, time, traceback, math
os.environ['KIVY_AUDIO']='sdl2'
import api

from random import choice

from mythread import myThread
from dialy import File
from myspider import Spider

import kivy
from kivy.app import App
from kivy.clock import Clock
from kivy.logger import Logger
from kivy.clock import mainthread
from kivy.core.text import LabelBase
from kivy.cache import Cache
from kivy.factory import Factory
from kivy.core.audio import SoundLoader
from kivy.utils import get_color_from_hex, escape_markup

def C(hex_color):
    return get_color_from_hex(hex_color)[:3]


from kivy.effects.scroll import ScrollEffect

is_android= kivy.platform == 'android'
if is_android:
    ScrollEffect.min_velocity=.5
    ScrollEffect.faster_rate=2
    ScrollEffect.friction=.05
else:
    ScrollEffect.min_velocity=.5
    ScrollEffect.faster_rate=2
    ScrollEffect.friction=.05


conf_dir = 'NEMbox/.netease-musicbox'

if is_android:
    from jnius import autoclass, cast
    from android.runnable import run_on_ui_thread
    from android.storage import primary_external_storage_path
    from android.permissions import request_permissions, Permission, check_permission
    MediaPlayer = autoclass('android.media.MediaPlayer')
    WindowManager = autoclass('android.view.WindowManager') 
    activity = autoclass('org.kivy.android.PythonActivity').mActivity 
    window = activity.getWindow();
    LayoutParams= autoclass('android.view.WindowManager$LayoutParams')
    currentActivity = cast('android.app.Activity', activity)

    @run_on_ui_thread
    def cancel_full_screen():
        window.clearFlags(1024)

    @run_on_ui_thread
    def move_task_to_back():
        currentActivity.moveTaskToBack(True)


    if check_permission(Permission.WRITE_EXTERNAL_STORAGE):
        conf_dir=os.path.join(primary_external_storage_path(), '.netease-musicbox')
    
    def callbk(list_perm ,list_result):
        for p,r in zip(list_perm, list_result):
            Logger.info('%s, %s'%(p,r))
            if 'WRITE_EXTERNAL_STORAGE' in p.upper() and r:
                global conf_dir
                conf_dir=os.path.join(primary_external_storage_path(), '.netease-musicbox')
                if not os.path.exists(conf_dir):
                    os.mkdir(conf_dir)
                Logger.info(conf_dir)

    # ask for permissions
    permissions=[Permission.WRITE_EXTERNAL_STORAGE]
    
    try:
        for p in permissions:
            if not check_permission(p):
                request_permissions([p], callback=callbk)
    except Exception as e:
        Logger.info(str(e))


class Block(Factory.Widget):
    block_lock=Factory.ListProperty([True,True,True])
    
    def on_touch_down(self, touch):
        super(Block, self).on_touch_down(touch)
        return self.block_lock[0]

    def on_touch_up(self, touch):
        super(Block, self).on_touch_up(touch)
        return self.block_lock[1]

    def on_touch_move(self, touch):
        super(Block, self).on_touch_move(touch)
        return self.block_lock[2]

class NetEaseApp(App):
    def __init__(self, debug_mood=False):
        super(NetEaseApp, self).__init__()
        self.init_kivy_conf()
        
        self.distribute_source_file_name()
        self.load_user_info()
        
        Window.bind(on_keyboard=self.touch_on_android_button)
        
        myThread(self.api_event_listener,[None], dont_join=1)

        self.debug_mood = debug_mood

    def run(self):
        try:
            super(NetEaseApp,self).run()
        except Exception as e:
            if self.is_android:
                with open(os.path.join(conf_dir,'A_debug.txt'), 'a')as f:
                    f.write(traceback.format_exc())
            else:raise e
        
    def log_info(self, msg):
        if self.debug_mood:
            @mainthread
            def f():
                self.root.ids['debug_label'].text+='\n'+str(msg)
            f()
        else:Logger.info(msg)

    def on_start(self):
        self.playbar=self.root.ids['playbar']
        from kivy.base import EventLoop
        myThread(self.update_user_playlist,[None], dont_join=1)

    def show_notice(self, title=None, content_text=None,
                    separator_color=None, ensure_text=None,
                    c0_a=None, content_c0=None):

        w=Factory.NoticeBox()
        
        w.title=title or w.title
        w.content_text=content_text or w.content_text
        w.separator_color=separator_color or self.root.light_bg_color_90
        w.ensure_text=ensure_text or w.ensure_text
        w.c0_a=c0_a or w.c0_a
        w.content_c0=content_c0 or self.root.bg_color
        
        Window.add_widget(w)
    
    def distribute_source_file_name(self):
        if not os.path.exists(conf_dir):
            os.mkdir(conf_dir)
    
        self.user_info_path=os.path.join(conf_dir, 'user_info.json')
        self.user_playlist_path=os.path.join(conf_dir, 'user_playlist.json')
        self.system_config_path=os.path.join(conf_dir,'sys_config.json')
        
        self.pl_head='p_c_'
        
        self.avatar_fn='src/avatar.jpg'
        self.avatar_id_list=['avatar_image_0','avatar_image_1']
        self.nickname_id_list=['avatar_text_0','avatar_text_1']
        self.favotie_music_list_id=None

        self.current_song=None
        self.current_song_length=0
        self.plarbar_ratio=.07
        self.music_pre_pos=None
        self.loop_status=1
        self.pausing=False
        self.player_monitor_actived=False
        self.playing_music_list_id=None
        self.playing_song={'id':None}
        
        self.current_sv_pos=0
        self.lock=False
        self.anim_lock=False
        self.lyric_monitor_actived=False
        self.lyric_update_cd_time=.2
        self.scrolled_time=0
        self.lyric_scroll_cd_time=3
        self.seeked_time=0
        self.seek_cd_time=1
        
        self.night=False

        self.total_loop_kind={0: 'src/single_loop.png', 1: 'src/order_play.png',
                              2: 'src/random_play.png'}
        
        self.played_on_android=False
        # if android
        self.is_android=is_android
        if self.is_android:
            self.is_android=True
            self.player = MediaPlayer()

        self.removed_widget_dict={}

        # colors
        self.colors={'red':[96.2/100, 20.9/100, 20.9/100],
                     'gray':[.99, .99, .99],
                     'dark_gray':[.9, .9, .9],
                     'white':[1, 1, 1],
                     'black':[0, 0, 0],
                     'green':[.258, .531, .025],
                     'light_black':[.271, .271, .271],
                     'hex_light_black':'#a0a0a0',
                     }
        other_beautiful_color=['#FF0000', '#00FF00', '#0000FF', '#FF00FF', '#00FFFF', '#FFFF00', '#000000', '#70DB93', '#5C3317', '#9F5F9F', '#B5A642', '#D9D919', '#A67D3D', '#8C7853', '#A67D3D', '#5F9F9F', '#D98719', '#B87333', '#FF7F00', '#42426F', '#5C4033', '#2F4F2F', '#4A766E', '#4F4F2F', '#9932CD', '#871F78', '#6B238E', '#2F4F4F', '#97694F', '#7093DB', '#855E42', '#545454', '#856363', '#D19275', '#8E2323', '#238E23', '#CD7F32', '#DBDB70', '#C0C0C0', '#527F76', '#93DB70', '#215E21', '#4E2F2F', '#9F9F5F', '#C0D9D9', '#A8A8A8', '#8F8FBD', '#E9C2A6', '#32CD32', '#E47833', '#8E236B', '#32CD99', '#3232CD', '#6B8E23', '#EAEAAE', '#9370DB', '#426F42', '#7F00FF', '#7FFF00', '#70DBDB', '#DB7093', '#A68064', '#2F2F4F', '#23238E', '#4D4DFF', '#FF6EC7', '#00009C', '#EBC79E', '#CFB53B', '#FF7F00', '#FF2400', '#DB70DB', '#8FBC8F', '#BC8F8F', '#EAADEA', '#D9D9F3', '#5959AB', '#6F4242', '#BC1717', '#238E68', '#6B4226', '#8E6B23', '#E6E8FA', '#3299CC', '#007FFF', '#FF1CAE', '#00FF7F', '#236B8E', '#38B0DE', '#DB9370', '#D8BFD8', '#ADEAEA', '#5C4033', '#CDCDCD', '#4F2F4F', '#CC3299', '#D8D8BF', '#99CC32']
        self.theme={'red':{'common':self.colors['red'],'text':self.colors['red'],},
                    'green':{'common':self.colors['green'],'text':self.colors['green'],},
                    'black':{'common':self.colors['black'],'text':self.colors['black'],},
                    'light_black':{'common':C(self.colors['hex_light_black']),'text':self.colors['light_black'],},
                    }
        other_theme={str(i):{'common':C(v)} for i,v in enumerate(other_beautiful_color)}
        self.theme.update(other_theme)
        
        if not os.path.exists(self.system_config_path):
            default_config={'theme': 'green'}
            File.save_to_json(default_config, self.system_config_path)
            self.system_config=default_config

        else:
            self.system_config=File.load_from_json(self.system_config_path)
        

    def load_user_info(self,):
        self.spider=api.NetEase()
        
        self.user_info=self.spider.storage.database['user'].get('detail') or {'profile':{'nickname':'游客','userId': '0000',}}
        self.nickname=self.user_info['profile']['nickname']
        self.id=self.user_info['profile']['userId']
        
    def init_kivy_conf(self,):
        self.font_size=25 if kivy.platform == 'linux' else 40
        self.width,self.height =Window.size
        self.S=kivy.effects.scroll.ScrollEffect

    def back(self):
        if self.root.ids['sidebar_g'].raised:self.touch_on_layout([None]*2,'menu')
            
        if self.root.current != 'home':
            self.switch_screen('home')
        else:
            if self.is_android:move_task_to_back()

            self.switch_glayout(0)

    def touch_on_android_button(self, window, key, *args):
        if key==27:
            self.back()
            return True

    def set_playbar_height_to_zero(self):
        if getattr(self,'playbar',None):
            self.playbar.size_hint_y=0

    def night_mood(self):
        color=self.colors['white'] if self.night else C('#8f8f8f')
        
        self.root.bg_color=color

        self.night=not self.night

    def change_theme(self, theme_name):
        if self.system_config['theme'] != theme_name:
            theme_color=self.theme[theme_name]['common']
            self.root.theme_color=theme_color
            
            self.system_config['theme']=theme_name
            File.save_to_json(self.system_config, self.system_config_path)
            

    def previous_elem(self, e, e_list):
        return e_list[(e_list.index(e)-1)%(len(e_list))]
    
    def next_elem(self, e, e_list):
        return e_list[(e_list.index(e)+1)%(len(e_list))]
    
    def get_pl_cover_by_id(self,id_):
        if id_=='0000': return 'src/cached_pl_cover.png'
        elif id_=='0001': return 'src/avatar.jpg'
        return os.path.join(conf_dir ,self.pl_head+str(id_)+'.jpg')

    def get_user_cover_by_id(self, id_):
        if id_ in (self.id, '0000', '0001'):return 'src/avatar.jpg'
        return os.path.join(conf_dir ,self.pl_head+'c_'+str(id_)+'.jpg')

    def get_song_preview_path_by_id(self,id_):
        return os.path.join(conf_dir ,self.pl_head+'p_s_'+str(id_)+'.json')
    
    def get_music_path_by_id(self, id_):
        return os.path.join(conf_dir ,self.pl_head+'m_'+str(id_)+'.mp3')

    def get_music_cover_path_by_id(self, id_):
        return os.path.join(conf_dir ,self.pl_head+'m_'+str(id_)+'.jpg')

    def get_pl_preview_path_by_id(self,id_):
        return os.path.join(conf_dir ,self.pl_head+'p_'+str(id_)+'.json')
    
    def get_pl_detail_path_by_id(self, id_):
        return os.path.join(conf_dir ,self.pl_head+'d_'+str(id_)+'.json')

    def get_pl_detail_by_id(self, id_):
        if id_ == '0000':
            return [File.load_from_json(f) for f in self.get_all_cached_song_path()]
        return File.load_from_json(self.get_pl_detail_path_by_id(id_))

    def get_last_date_path(self):
        return os.path.join(conf_dir, 'last_date.json')

    def get_daily_rec_playlists(self):
        return os.path.join(conf_dir, 'daily_rec_playlists.json')

    def get_all_cached_pl_preview_path(self):
        return [os.path.join(conf_dir,f) for f in os.listdir(conf_dir) \
                if re.findall('p_\d+\.json', f)]

    def get_all_cached_song_path(self):
        return sorted((os.path.join(conf_dir,f) \
                       for f in os.listdir(conf_dir) if re.findall('p_s_\d+\.json',f)),
                      key=os.path.getctime)

    def get_user_playlist_by_id(self, id_):
        return os.path.join(conf_dir, 'user_pl_'+str(id_)+'.json')

    def get_song_lyric_path_by_id(self, id_):
        return os.path.join(conf_dir, 'song_ly'+str(id_)+'.json')

    def login_by_pd(self):
        def f():
            username=self.root.ids.t_i_un.text
            passwd=self.root.ids.t_i_pd.text
            self.spider.logout()
            if self.spider.login(username, passwd, need_md5_enc=1):
                self.log_info('Login Successful !')

                # pack_up sidebar
                @mainthread
                def f1():
                    self.touch_on_layout([None]*2, do_this_anyway='menu', other_params='no_anim')
                f1()
                self.switch_screen('home')
                self.update_resource_after_login()
                
            else:
                self.log_info('Bad passwdord or username.')
                self.show_notice()
                
        myThread(f, [None],dont_join=1)
        
    def login(self):
        self.switch_screen('login')

    def logout(self):
        self.login()
        
    def clear_conf(self):
        for f in os.listdir(conf_dir):
            os.remove(os.path.join(conf_dir,f))
            
    def download_resource(self,url,filename, binary=True):
        self.log_info('DownLoading %s'%filename)
        r=Spider(url).get()
        if binary:File.save_to_file(r.content, filename)
        else: File.save_to_file(r.text, filename)
        
    def update_resource_after_login(self):
        self.load_user_info()
        
        myThread(self.update_image, [None], dont_join=1)
        myThread(self.update_text, [None], dont_join=1)
        myThread(self.update_user_playlist,[None], dont_join=1)

    def update_text(self, ):
        myThread(self._update_nickname, [self.nickname_id_list], dont_join=1)

    def update_image(self,):
        # clear cache about avatar
        @mainthread
        def f():
            [Cache.remove(category,key) for category in ('kv.image', 'kv.texture') \
                   for key in list(Cache._objects[category].keys())\
                   if 'avatar.jpg' in key
                   ]
        f()
        
        myThread(self._update_avater, [self.avatar_id_list], dont_join=1)

    def _update_nickname(self, nickname_id_list):
        nickname=self.user_info['profile']['nickname']
        for l in nickname_id_list:
            self.update_label_text(l, nickname)
            
 
    def _update_avater(self, avater_id_list, need_dowload=True):
        url=self.user_info['profile']['avatarUrl'] # avatarUrl
        if need_dowload: self.download_resource(url,self.avatar_fn)

        length=len(avater_id_list)
        for i,l in enumerate(avater_id_list):
            self._update_canvas(l)

    @mainthread
    def update_image_source(self,id_, new_source=None, need_reload=False):
        layout=self.root.ids[id_] if type(id_)==str else id_
        if new_source:layout.source=new_source
        if need_reload:layout.reload()
        return 

    @mainthread
    def update_label_text(self, id_, text, layout_type=0):
        if layout_type==0:
            layout=self.root.ids[id_]
        elif layout_type==1:
            layout=self.root.ids[id_]
        layout.text=text

    @mainthread
    def _update_canvas(self, id_):
        # dirty but have to do these
        self.root.ids[id_].update_controler=True
        self.root.ids[id_].update_controler=False

    def api_event_listener(self):
        while 1:
            got=api.q_put.get(None)
            
            if got=='input_un_pd':
                self.login()

    def update_user_playlist(self, only_from_local_file=False):
        user_pl=self.spider.user_playlist()
        pl_path=self.get_user_playlist_by_id(self.id)
        
        if user_pl:File.save_to_json(user_pl, pl_path)
        else:user_pl=File.load_from_json(pl_path)
        
        playlist=self.parse_playlist(user_pl, do_classify=True)
        

        created_pl=[]
        collected_pl=[]

        for pl in playlist:
            # find the user's favorite musiclist id
            if pl['name']== self.nickname+'喜欢的音乐': self.favotie_music_list_id=pl['id']
            
            if pl['classify']==0:created_pl.append(pl)
            elif pl['classify']==1:collected_pl.append(pl)

        playlist=[created_pl,collected_pl]
        self._update_user_playlist(playlist)

    def _update_user_playlist(self, playlist):
        self.clear_glayout('created')
        self.clear_glayout('collected')

        created_pl,collected_pl=playlist
        
        @mainthread
        def f():
            layout=self.root.ids['created_m_l_m']
            layout.t0=re.sub('\d+',str(len(created_pl)),layout.t0)
            
            layout=self.root.ids['collected_m_l_m']
            layout.t0=re.sub('\d+',str(len(collected_pl)),layout.t0)

        f()
        myThread(self.add_single_playlist,
                 list(zip(created_pl, ['created']*len(created_pl))), dont_join=1)
        
        myThread(self.add_single_playlist,
                 list(zip(collected_pl, ['collected']*len(collected_pl))), dont_join=1)
        

    def add_single_playlist(self, playlist, parent, type_=0):
        id_,img,name,creator= [playlist[x] for x in ['id','coverImgUrl','name','creator']]
        
        if type_==0:t1='0首 by %s'%creator
        
        img_fn=self.get_pl_cover_by_id(id_)
        
        if not os.path.exists(img_fn):self.download_resource(img,img_fn)

        if type_==0:
            self.add_layout(0,parent,t0=name,t1=t1,i0=img_fn, playlist_id=id_)
        elif type_==1:
            self.add_layout(2,parent,s0=img_fn,t0=name,playlist_id=str(id_))

    def parse_songs(self, songs):
        for s in songs:
            s['img_url']=s['al']['picUrl'] if s.get('al') else s['album']['artist']['img1v1Url']
            s['author_name']=(s.get('ar') or s['artists'])[0]['name']
        return songs

    @mainthread
    def add_songs_from_playlist(self,playlist_id,
                                screen_name='music_list',glayout_name='playlist_songs'):
        
        this_screen=self.root.get_screen(screen_name)
        
        # playlist songs
        if type(playlist_id)==str:
            if playlist_id=='0000':
                pl_detail=[File.load_from_json(f) for f in self.get_all_cached_song_path()]
                pl_detail=self.parse_songs(pl_detail)
            elif playlist_id=='0001':
                pl_detail=self.spider.recommend_playlist()
                pl_detail=self.parse_songs(pl_detail)
            else:
                pl_path=self.get_pl_detail_path_by_id(playlist_id)
                ori_pl_detail=self.spider.playlist_detail(playlist_id)
                if ori_pl_detail:
                    pl_detail=self.parse_songs(ori_pl_detail)
                    File.save_to_json(pl_detail,pl_path)
                else:pl_detail=File.load_from_json(pl_path)

            this_screen.current_pl_id=playlist_id

        # search songs
        else:
            pl_detail=playlist_id
            pl_detail=self.parse_songs(pl_detail)
            
        pl_detail=list(pl_detail)
        this_screen.current_playlist=pl_detail

        layout=self.root.ids.m_l_sv if self.root.current=='music_list' else self.root.ids.search_m_l_sv
        layout.data = [{'n0':str(i), 't0':song['name'][:23], 't1':song['author_name'][:23], 'd_info':song}\
                       for i,song in enumerate(pl_detail, start=1)]

        @mainthread
        def f():
            layout.scroll_y=1
            layout.update_from_scroll()
        f()

    @mainthread
    def add_layout(self, layout_type, parent, *_,**kw):
        if layout_type==0:
            l=Factory.PlaylistGlayout
            
        elif layout_type==1:
            l=Factory.SingleMusicGlayout

        elif layout_type==2:
            l=Factory.RecommendPlaylist

        w=l(**kw)
        if layout_type==1 and int(kw['n0'])%10 == 1:
            self.first_added_song=(int(kw['n0']), w)
        self.root.ids[parent].add_widget(w)
        
    @mainthread
    def move_widget_pos(self, id_, pos):
        layout=self.root.ids[id_]
        layout.pos=pos
        
    @mainthread
    def clear_glayout(self, g_name, key_name=None):
        layout=self.root.ids[g_name]

        if key_name:
            self.removed_widget_dict[key_name]=[]
            while layout.children:
                first_children=layout.children[0]
                self.removed_widget_dict[key_name].append(first_children)
                layout.remove_widget(first_children)

        else:
            while layout.children:
                first_children=layout.children[0]
                layout.remove_widget(first_children)
        

    
    def play_a_new_song(self,song):
        self.lock=True
        self.log_info('Lock Acquired.')
        # Player Monitor
        if not self.player_monitor_actived :
            self.player_monitor_actived=True
            myThread(self.song_player_moniter,[None], dont_join=1)
            
        self.update_label_text('playbar_song_name',song['name'])
        @mainthread
        def f():
            self.root.is_playing=True
        f()
        
        # update the music cover image of playbar
        def f():
            music_cover_path=self.get_music_cover_path_by_id(song['id'])

            if not os.path.exists(music_cover_path):
                cover_url=song['img_url']
                self.download_resource(cover_url, music_cover_path)

            self.update_image_source('current_song_cover', music_cover_path)

        myThread(f, [None], dont_join=True)
        
        # if not android
        if not self.is_android:
            @mainthread
            def f():
                if self.current_song:
                    if self.playing_song['id'] != song['id']:
                        self.current_song.stop()
                        self.current_song.unload()

                else:
                    self.playbar.size_hint_y=self.plarbar_ratio
            f()
            
        else:
            if not self.played_on_android:
                @mainthread
                def f():
                    self.playbar.size_hint_y=self.plarbar_ratio
                f()
                self.played_on_android=True

            if self.playing_song['id'] != song['id']:
                self.player.reset()
            
        song_path=self.get_music_path_by_id(song['id'])
        
        if not os.path.exists(song_path):
            try:
                url=self.spider.songs_url([song['id']])[0]['url']
                if not url:
                    raise ValueError('')

            except Exception as e:
                self.update_label_text('playbar_song_name','抱歉，无法播放该音乐,一秒后播放下一首')
                @mainthread
                def f():
                    self.root.is_playing=False
                f()
                time.sleep(1)
                
                return myThread(self.play_a_new_song, [self.next_elem(song, self.playing_music_list)], dont_join=True)
            
            self.download_resource(url,song_path)

            # record to cached
            File.save_to_json(song,self.get_song_preview_path_by_id(song['id']))
            

        # if not android
        if not self.is_android:
            @mainthread
            def f():
                if self.playing_song['id'] != song['id']:
                    self.current_song=SoundLoader.load(song_path)
                    
                self.current_song.play()
                self.current_song.seek(0)

                self.playing_song=song
                
                self.lock=False
                self.log_info('Lock Release.')
                
            f()
            
        else:
            if self.playing_song['id'] != song['id']:
                self.player.setDataSource(song_path)
                self.player.prepare()
            else:
                self.android_seek_to(0)
                
            self.player.start()

            self.playing_song=song
            
            self.lock=False
            self.log_info('Lock Release.')
        
        # update all thing in screen: 'music_lyric'
        self.update_lyric(song)

    def android_seek_to(self, to):
        self.seeked_time=time.time()
        try:
            self.player.seekTo(to, 0)
            self.log_info('Seek Method 0')
        except:
            try:
                self.player.seekTo(to)
                self.log_info('Seek Method 1')
            except:
                self.log_info('Fuck Seek.')

    def is_liked_music(self, music_id):
        if self.favotie_music_list_id is None:return False

        return self.favotie_music_list_id and str(music_id) in [str(s['id']) for s in self.spider.playlist_detail(self.favotie_music_list_id)]

    def format_time(self, sec):
        return ':'.join([str(x).zfill(2) for x in divmod(int(sec),60)])
    
    def update_lyric(self, song):
        self.update_label_text('ly_sn',song['name'])
        self.update_label_text('ly_an',song['author_name'])

        # is liked music
        def f():
            liked=self.is_liked_music(song['id'])
            @mainthread
            def f1():
                self.root.get_screen('song_lyric').liked=liked
            f1()
        myThread(f, [None], dont_join=True)
        
        song_lyric_path=self.get_song_lyric_path_by_id(song['id'])
        if not os.path.exists(song_lyric_path):
            song_lyric=self.spider.song_lyric(song['id'])
            File.save_to_json(song_lyric, song_lyric_path)
        else:song_lyric=File.load_from_json(song_lyric_path)

        song_lyric = [s for s in song_lyric if re.findall('^\[\d', s)]
        time_dict={sum([
            float(t)*60**(1-r) for r,t in enumerate((re.findall('[\d\.:]+', head)[0]).split(':'))
            ]):body for sentence in song_lyric if sentence.strip() for head,body in [sentence.split(']')] }

        self.root.get_screen('song_lyric').lyric_dict=time_dict
        l=self.root.ids['lyric_label']
        empty_lines_n=math.ceil(l.parent.parent.height/2/l.line_height/l.font_size)
        
        # must have somthimg for anchor
        self.update_label_text('lyric_label', '\n'.join(
            ['[anchor=%s]%s'%(str(i),escape_markup(v or ' ')) \
             for i,v in enumerate([' ']*empty_lines_n+list(time_dict.values())+[' ']*empty_lines_n,
                                  start=-empty_lines_n)]))
        
        @mainthread
        def f():
            if not self.is_android:
                self.current_song_start_time=time.time()
                self.current_song_length=self.current_song.length
            else:
                self.current_song_length=self.player.getDuration() / 1000
                
            self.root.ids['song_length'].text=self.format_time(self.current_song_length)
                
            if not self.lyric_monitor_actived:
                myThread(self.lyric_moniter, [None], dont_join=True)
                self.lyric_monitor_actived=True
        f()

    def lyric_moniter(self, ):
        slider_update_n=0
        while True:
            time.sleep(self.lyric_update_cd_time)
            
            if self.root.current != 'song_lyric' or self.lock:continue
            
            slider_update_n=(slider_update_n+1)%5
            l=self.root.ids['lyric_label']
            if not self.is_android:
                c_time=time.time()-self.current_song_start_time
            else:
                c_time=self.player.getCurrentPosition() / 1000

            c_play_rate=c_time/self.current_song_length if self.current_song_length else 0
            
            c_index=-1
            for t in self.root.get_screen('song_lyric').lyric_dict.keys():
                if c_time<float(t):break
                c_index+=1
                
            @mainthread
            def f():
                if not self.root.ids['play_slider'].lock and slider_update_n==0:
                    self.root.ids['play_slider'].value_normalized=c_play_rate
                    
                if time.time()-self.scrolled_time<self.lyric_scroll_cd_time:return
                
                p=l.parent.parent
                if not l.anchors:
                    l.texture_update()
                anchor=l.anchors.get(str(c_index))
                if not anchor:
                    self.log_info('...'+str(c_index))
                    return
                
                rate=(anchor[1]-p.height/2)/(l.height-p.height)
                
                p.scroll_y=max(1-rate, 0)
                p.update_from_scroll()
            f()
        
    def song_player_moniter(self):
        while True:
            lock=self.lock or time.time()-self.seeked_time < self.seek_cd_time
            if self.lock:
                pass
            
            elif not self.pausing and ((not self.is_android and self.current_song.state=='stop') or \
                                       self.is_android and not self.player.isPlaying()):
                
                self.play_next_song()

            time.sleep(.2)

    def play_next_song(self, force_code=None):
        option_code = force_code or self.loop_status
        if option_code==0:
            myThread(self.play_a_new_song, [self.playing_song], dont_join=True)

        elif option_code==1:
            myThread(self.play_a_new_song, [self.next_elem(self.playing_song, self.playing_music_list)], dont_join=True)
        
        elif option_code==2:
            myThread(self.play_a_new_song, [choice(self.playing_music_list)], dont_join=True)

        elif option_code==3:
            myThread(self.play_a_new_song, [self.previous_elem(self.playing_song, self.playing_music_list)], dont_join=True)
 
    @mainthread
    def play_or_stop_current_song(self):
        layout=self.root.ids['playbar_status']
        self.root.is_playing=not self.root.is_playing
        # if not android
        if not self.is_android:
            if self.current_song:
                if self.current_song.state=='stop':
                    self.current_song.play()
                    self.current_song.seek(self.music_pre_pos)
                    self.pausing=False
                      
                else:
                    self.music_pre_pos=self.current_song.get_pos()
                    self.current_song.stop()
                    self.pausing=True

        else:
            if self.player.isPlaying():
                self.player.pause()
                self.pausing=True
            else:
                self.player.start()
                self.pausing=False

    
    def parse_playlist(self, playlist, do_classify=False):
        user_playlist=[self.parse_single_playlist(pl, do_classify=do_classify) for pl in playlist]
        
        return user_playlist

    def parse_single_playlist(self,pl, auto_save=True, do_classify=False):
        info={'creator':pl['creator']['nickname'],
              'id': str(pl['id']),
              'name': pl['name'],
              'coverImgUrl': pl.get('coverImgUrl') or pl['picUrl'],
              'creator_img': pl['creator']['avatarUrl'],
              'creator_id': str(pl['creator']['userId']),
              }
        # 0:created, 1:collected, 2:other
        if do_classify:
            try:
                t=0 if pl['creator']['userType']==0 else 1
            except KeyError:
                t=2
            info['classify']=t

        if auto_save:
            File.save_to_json(info,self.get_pl_preview_path_by_id(info['id']))

        return info

    def switch_to_music_list(self,pl_id):
        self.switch_screen('music_list')
        # normal playlist
        if self.root.get_screen('music_list').current_pl_id==pl_id and pl_id!='0000':
            return

        pl_path=self.get_pl_preview_path_by_id(pl_id)
        
        if pl_id=='0000':
            pl={'creator': self.nickname,
                'id': '0000',
                'name':'缓存的音乐',
                'coverImgUrl':'src/avatar.jpg',
                'creator_id': self.id,
                'classify': 2}
        elif pl_id=='0001':
            pl={'creator': self.nickname,
                'id': '0001',
                'name':'每日推荐',
                'coverImgUrl':'src/avatar.jpg',
                'creator_id': self.id,
                'classify': 2}
        else:
            pl=File.load_from_json(pl_path)
                

        self.update_label_text('creator_name', pl['creator'])
        self.update_label_text('pl_name', pl['name'])
        self.update_image_source('big_pl_cover',self.get_pl_cover_by_id(pl['id']))

        creator_img= self.get_user_cover_by_id(pl['creator_id'])

        def f():
            if not os.path.exists(creator_img):
                self.download_resource(pl['creator_img'], creator_img)
                
            self.update_image_source('creator_avatar', creator_img)
        myThread(f, [None], dont_join=True)

        self.add_songs_from_playlist(pl_id)

    def do_search(self, key_word):
        search_result_songs=self.spider.search(key_word).get('songs', [])
        self.add_songs_from_playlist(search_result_songs,'search','search_pl_g')
        
    def update_daily_recommend_pl(self):
        rec_pl=[self.parse_single_playlist(pl) for pl in self.spider.recommend_resource()]

        layout=self.root.ids['recommand_m_l']
        
        pre_pl_ids=[c.playlist_id for c in layout.children if type(c)==Factory.RecommendPlaylist]
        new_pl_ids=[pl['id'] for pl in rec_pl]

        
        will_remove=[]
        for l in (l for l in layout.children \
                  if type(l)==Factory.RecommendPlaylist and l.playlist_id not in new_pl_ids):
            will_remove.append(l)
            pre_pl_ids.remove(l.playlist_id)

        @mainthread
        def f():
            for l in will_remove:
                layout.remove_widget(l)
        f()

        for pl in rec_pl:
            if pl['id'] not in pre_pl_ids:
                self.add_single_playlist(pl,'recommand_m_l',type_=1)

    def delete_music(self, song_widget):
        d_info=song_widget.d_info
        p=song_widget.parent.parent
        try:
            funcs=[self.get_song_lyric_path_by_id, self.get_music_cover_path_by_id,
                   self.get_song_preview_path_by_id, self.get_music_path_by_id,
                   ]
            for f in funcs:os.remove(f(d_info['id']))
            
            p.data.pop(list(map(lambda x:x['d_info'], p.data)).index(d_info))
        except:self.log_info('Delete Error')
        else:self.log_info('Deleted')
    
    def touch_on_layout(self, args, do_this_anyway=None, other_params=None):
        instance, value = args
        if do_this_anyway or instance.collide_point(*value.pos):
            idd=instance.idd if not do_this_anyway else do_this_anyway
            
            layout=self.root.ids.sidebar_g
            if not do_this_anyway:
                if instance.to_window(*value.pos)[1]<self.playbar.height and \
                   idd not in ('play_or_stop', 'change_loop_status', 'song_detail',
                               'play_previous_song', 'play_next_song', 'like'):
                    return

            if idd=='menu':
                layout=self.root.ids['sidebar_g']
                width=self.root.width

                if layout.raised:
                    to=-1*width
                    opacity=0
                else:
                    to=0
                    opacity=.5
                    
                def on_c(*_):
                    layout.raised=not layout.raised
                
                def on_s(*_):
                    if not layout.raised:
                        if self.playbar.height:
                            self.playbar.size_hint_y=0

                duration=.2 if other_params!='no_anim' else 0
                anim = Factory.Animation(x=to, duration=duration, t='out_cubic')
                anim.on_start=on_s
                anim.on_complete=on_c
                anim_1 = Factory.Animation(opacity=opacity, duration=duration, t='out_cubic')
                anim.start(layout)
                anim_1.start(self.root.ids['shadow'])
                
            elif idd=='login':
                self.login_by_pd()
                
            elif idd=='back':
                self.back()

            elif idd=='textinput':
                if self.is_android:
                    instance.focus=False
                    instance.focus=True
                
            elif idd=='music':
                breakpoint()
                self.switch_glayout(0,)
                
            elif idd=='wyy':
                self.switch_glayout(1,)
                myThread(self.update_daily_recommend_pl,[None],dont_join=1)

            elif idd=='video':
                self.switch_glayout(2,)

            elif idd=='search':
                self.switch_screen('search')

            elif idd=='local_music':
                myThread(self.switch_to_music_list,['0000'],dont_join=1)
                
            elif idd=='recommand':
                self.move_mark_line(0)
                self.switch_glayout(1,0)
                
            elif idd=='friend':
                self.move_mark_line(1)
                self.switch_glayout(1,1)
                
            elif idd=='radio':
                self.move_mark_line(2)
                self.switch_glayout(1,2)

            elif idd=='date':
                def f():
                    self.switch_to_music_list('0001')
                myThread(f, [None], dont_join=True)


            elif idd=='check_in':
                layout=self.root.ids.sidebar_left_label
                layout.text='签签签'
                
            elif idd=='message':
                layout=self.root.ids.sidebar_left_label
                layout.text='木有消息哦'

            elif idd=='vip':
                layout=self.root.ids.sidebar_left_label
                layout.text='开个锤锤'

            elif idd=='ticket':
                layout=self.root.ids.sidebar_left_label
                layout.text='没票'

            elif idd=='shop':
                layout=self.root.ids.sidebar_left_label
                layout.text='没货'
                
            elif idd=='theme':
                self.change_theme(self.next_elem(self.system_config['theme'], list(self.theme.keys())))

            elif idd=='night':
                self.night_mood()

            elif idd=='setting':
                layout=self.root.ids.sidebar_left_label
                layout.text='设置啥'

            elif idd=='exit':
                self.logout()

            elif idd=='music_list':
                if instance.children[0].collide_point(*value.pos):
                    self.log_info('Setting')
                    
                else:
                    myThread(self.switch_to_music_list,[instance.playlist_id],dont_join=1)

            elif idd=='created_m_l_m':
                layout=self.root.ids.created
                
                l_height=self.root.height*.1
                for l in layout.children:
                    l.height = (l_height if l.height==0 else 0)

                instance.opened=not instance.opened

            elif idd=='collected_m_l_m':
                layout=self.root.ids.collected
                
                l_height=self.root.height*.1
                for l in layout.children:
                    l.height = (l_height if l.height==0 else 0)

                instance.opened=not instance.opened

            elif idd=='play_or_stop':
                self.play_or_stop_current_song()

            elif idd=='song':
                if instance.children[0].collide_point(*value.pos):
                    return
                
                m_l_id=self.root.current_screen.current_pl_id
                if m_l_id != self.playing_music_list_id:
                    self.playing_music_list_id=m_l_id
                    self.playing_music_list=self.root.current_screen.current_playlist
                elif self.root.current == 'search':
                    self.playing_music_list=self.root.current_screen.current_playlist

                myThread(self.play_a_new_song,[instance.d_info],dont_join=1)

            elif idd=='search_music':
                key_word=self.root.ids['search_bar'].text or self.root.ids['search_bar'].hint_text
                myThread(self.do_search,[key_word],dont_join=1)

            elif idd=='play_all_songs':
                # pass if empty playlist
                if not self.root.current_screen.current_playlist:
                    return True
                
                m_l_id=self.root.current_screen.current_pl_id
                if m_l_id != self.playing_music_list_id:
                    self.playing_music_list_id=m_l_id
                    self.playing_music_list=self.root.current_screen.current_playlist
                elif self.root.current == 'search':
                    self.playing_music_list=self.root.current_screen.current_playlist
                
                myThread(self.play_a_new_song,[self.playing_music_list[0]],dont_join=1)

            elif idd=='change_loop_status':
                self.loop_status = self.next_elem(self.loop_status, list(self.total_loop_kind.keys()))
                self.playbar.loop_status=self.loop_status
                self.log_info(self.loop_status)

            elif idd=='song_detail':
                # detect children's task
                children_ids=['playbar_status', 'loop_stt',]
                for c in children_ids:
                    if self.root.ids[c].collide_point(*value.pos):
                        return
                
                self.switch_screen('song_lyric', move_playbar=False)

            elif idd=='play_slider':
                if other_params=='on':
                    instance.lock=True
                    self.log_info('on')
                    
                else:
                    if not instance.lock or not self.current_song_length:
                        return True

                    instance.lock=False
                    
                    time_seek_to=self.current_song_length*self.root.ids['play_slider'].value_normalized
                    
                    if self.is_android:
                        self.android_seek_to(time_seek_to*1000)
                    else:
                        self.log_info('seek to %s'%time_seek_to)

            elif idd=='play_previous_song':
                self.play_next_song(3)
                
            elif idd=='play_next_song':
                self.play_next_song()

            elif idd=='show_song_bubble':
                
                w=Factory.MusicBubble()
                w.width=sum((x.width for x in w.content.children))
                x,y=instance.to_window(*value.pos)

                pos_hint=(x-w.width)/Window.width, y/Window.height
                w.pos_hint={'x':pos_hint[0], 'y':pos_hint[1]}
                
                # song info
                w.selected_widget=instance.parent
                Window.add_widget(w)

            elif idd=='like':
                screen=self.root.get_screen('song_lyric')
                screen.liked= not screen.liked
                myThread(self.spider.fm_like, [(self.playing_song['id'],screen.liked)], dont_join=True)
                
            elif idd=='debug':
                breakpoint()
                
            return True

    def touch_scrllview(self, args, touch_on=True):
        instance, value = args
        
        if self.root.current=='song_lyric' and self.scrolled_time==float('inf'):
            self.scrolled_time=time.time()
            return True
        
        if not self.player_monitor_actived or self.root.ids['common_box'].collide_point(*value.pos)\
           or self.root.current in ('login',):
            return True
        
        if instance.collide_point(*value.pos):
            if touch_on:
                if self.root.current=='song_lyric':
                    self.scrolled_time=float('inf')
                    
                self.current_sv_pos= value.pos[1]
                
            else:
                dis=self.current_sv_pos-value.pos[1]
                if dis<-10:
                    if self.playbar.height:self.playbar.size_hint_y=0
                elif dis>10:
                    if self.playbar.height==0:self.playbar.size_hint_y=self.plarbar_ratio

            return True

    def debug(self):
        self.debug_list=[]
        while 1:
            if self.debug_list:
                try:
                    code, option = self.debug_list.pop(0)
                    self.root.ids['debug_label'].text+='\n' + str(eval(option) if code else exec(option))
                except: self.root.ids['debug_label'].text+='\n' + traceback.format_exc()
            else:time.sleep(.3)

    @mainthread
    def switch_screen(self, screen_name, move_playbar=True):
        if move_playbar:
            self.playbar.parent.remove_widget(self.playbar)
            layout=self.root.get_screen(screen_name)
            layout.add_widget(self.playbar)

        self.root.current=screen_name

    def switch_glayout(self,screen_widget_index=None,layout_index=None):
        if screen_widget_index != None:
            # change image alpha
            self.root.ids['common_0'].focus_n=screen_widget_index
            
            screen_widget_list=['first_page_s','second_page_glayout','third_page_s']
            
            for x in range(screen_widget_index):
                layout=self.root.ids[screen_widget_list[x]]
                layout.width=0

            layout=self.root.ids[screen_widget_list[screen_widget_index]]
            layout.width=self.root.width

        layout_list=['first_page_2_s','second_page_2_s','third_page_2_s']
        if screen_widget_index==1:
            if layout_index != None:
                for x in range(layout_index):
                    layout=self.root.ids[layout_list[x]]
                    layout.width=0
            else:layout_index=self.root.ids.w_u_l.index
                
            layout=self.root.ids[layout_list[layout_index]]
            layout.width=self.root.width
            
        elif screen_widget_index==2:
            for l in layout_list:
                self.root.ids[l].width=0

    def move_mark_line(self,pos_index):
        l=self.root.ids.w_u_l
        l.index=pos_index


if __name__ == '__main__':
    from kivy.config import Config
    from kivy.core.window import Window
##    Config.set('kivy', 'log_dir', conf_dir)
##    Config.set('kivy', 'log_enable', 1)
##    Config.set('kivy', 'log_name', 'debug.txt')
##    Config.set('kivy', 'log_level', 'info')
    
    
    if kivy.platform != 'linux':
        # remove all breakpoints even if i forgot it,  ( ~>-<~ )
        breakpoint=lambda:None
        
##    else:
##        Window.size=[800/16*9,800]
    
    LabelBase.register(name='kai', fn_regular='src/kai.ttf', fn_bold='src/kai.ttf')
    
    NetEaseApp(False).run()





















