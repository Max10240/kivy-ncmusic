import sys
sys.path.append('./NEMbox')

import os, re, time, traceback

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
from kivy.factory import Factory
from kivy.core.audio import SoundLoader
from kivy.utils import get_color_from_hex as C


from kivy.effects.scroll import ScrollEffect

is_android= kivy.platform == 'android'
if is_android:
    ScrollEffect.min_velocity=700
    ScrollEffect.faster_rate=5
    ScrollEffect.friction=.1
else:
    ScrollEffect.min_velocity=.5
    ScrollEffect.faster_rate=2
    ScrollEffect.friction=.05


conf_dir = 'NEMbox/.netease-musicbox'

if is_android:
    from android.storage import primary_external_storage_path
    from android.permissions import request_permissions, Permission, check_permission

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

    permissions=[Permission.WRITE_EXTERNAL_STORAGE, Permission.ACCESS_FINE_LOCATION]

    for p in permissions:
        if not check_permission(p):
            request_permissions([p], callback=callbk)



class NetEaseApp(App):
    def __init__(self):
        App.__init__(self)
        self.init_kivy_conf()
        
        self.distribute_source_file_name()
        self.load_user_info()
        
        Window.bind(on_keyboard=self.touch_on_android_button)
        
        myThread(self.api_event_listener,[None], dont_join=1)
        myThread(self._init, [None], dont_join=1)
        

    def on_start(self):
        self.playbar=self.root.ids['playbar']
        from kivy.base import EventLoop
        EventLoop.window.bind(on_keyboard=self.touch_on_android_button)
        myThread(self.update_user_playlist,[None], dont_join=1)


    def distribute_source_file_name(self):
        if not os.path.exists(conf_dir):
            os.mkdir(conf_dir)
    
        self.user_info_path='NEMbox/.netease-musicbox/user_info.json'
        self.user_playlist_path='NEMbox/.netease-musicbox/user_playlist.json'
        self.system_config_path=os.path.join(conf_dir,'sys_config.json')
        
        self.pl_head='p_c_'
        
        self.avatar_fn='src/avatar.jpg'
        self.avatar_id_list=['avatar_image_0','avatar_image_1']
        self.nickname_id_list=['avatar_text_0','avatar_text_1']

        self.current_song=None
        self.default_volume=.007
        self.music_pre_pos=None
        self.loop_status=1
        self.pausing=False
        self.player_monitor_actived=False
        self.playing_music_list_id=None
        self.playing_song={'id':None}
        self.lock=False
        self.anim_lock=False
        self.current_sv_pos=0

        self.total_loop_kind=[0, 1, 2]
        
        self.played_on_android=False
        # if android
        self.is_android=is_android
        if self.is_android:
            self.is_android=True
            
            from jnius import autoclass
            MediaPlayer = autoclass('android.media.MediaPlayer')
            self.player = MediaPlayer()

        self.removed_widget_dict={}

        # colors
        self.colors={'red':(96.2/100, 20.9/100, 20.9/100),
                     'gray':(.99, .99, .99),
                     'dark_gray':(.9, .9, .9),
                     'white':(1, 1, 1),
                     'black':(0, 0, 0),
                     'green':(.258, .531, .025),
                     'light_black':(.271, .271, .271),
                     'hex_light_black':'#a0a0a0',
                     }
        self.theme={'red':{'common':self.colors['red'],'text':self.colors['red'],},
                    'green':{'common':self.colors['green'],'text':self.colors['green'],},
                    'black':{'common':self.colors['black'],'text':self.colors['black'],},
                    'dark_gray':{'common':self.colors['dark_gray'],'text':self.colors['dark_gray'],},
                    'light_black':{'common':self.colors['light_black'],'text':self.colors['light_black'],},
                    }

        if not os.path.exists(self.system_config_path):
            default_config={'theme': 'green'}
            File.save_to_json(default_config, self.system_config_path)
            self.system_config=default_config

        else:
            self.system_config=File.load_from_json(self.system_config_path)
        

    def load_user_info(self,):
        
        if not os.path.exists(self.user_info_path):
            self.user_info={
                'profile':{'nickname':'游客',
                           'userId': '0000',},
                      }
            File.save_to_json([], self.get_user_playlist_by_id('0000'))
            
            File.save_to_json(self.user_info ,self.user_info_path)
        else:
            self.user_info=File.load_from_json(self.user_info_path)
            
        self.nickname=self.user_info['profile']['nickname']
        self.id=self.user_info['profile']['userId']
        
    def init_kivy_conf(self,):
        self.font_size=25 if kivy.platform == 'linux' else 40
        self.width,self.height =Window.size
        self.S=kivy.effects.scroll.ScrollEffect
        
    def _init(self,):
        self.spider=api.NetEase()

    def touch_on_android_button(self, window, key, *args):
        if key==27:
##            breakpoint()
##            return 
            if self.root.ids['sidebar_g'].raised:self.touch_on_layout([None]*2,'menu')
            
            if self.root.current != 'home':
                self.switch_screen('home')
            else:
                pass
            
            return True
        
    def change_theme(self, theme_name):
        if self.system_config['theme'] != theme_name:
            for screen in self.root.screens:
                for widget in screen.walk():
                    if type(widget) in (Factory.RedGridLayout, Factory.RedFloatLayout, ):
                        widget.canvas.before.children[0].rgb=self.theme[theme_name]['common']

            for widget in self.root.ids['func_box'].children:
                if type(widget) == Factory.ToolGLayout:
                    widget.c0=self.theme[theme_name]['common']

            text_id_list=['vip',]
            for w in text_id_list:
                self.root.ids[w].color=self.theme[theme_name]['common']+(1,)

            canvas_id_list=['vip_round', 'user_info_box', 'space_red', 'box_pic_fm']
            for w in canvas_id_list:
                self.root.ids[w].c0=self.theme[theme_name]['common']

            self.system_config['theme']=theme_name
            
            File.save_to_json(self.system_config, self.system_config_path)

    def next_elem(self, e, e_list):
        return e_list[(e_list.index(e)+1)%(len(e_list))]
    
    def get_pl_cover_by_id(self,id_):
        if id_=='0000':return 'src/cached_pl_cover.png'
        return os.path.join(conf_dir ,self.pl_head+str(id_)+'.jpg')

    def get_user_cover_by_id(self, id_):
        if id_=='0000':return 'src/avatar.jpg'
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
            if self.spider.login(username, passwd, need_md5_enc=1):
                Logger.info('Login Successful !')
                time.sleep(.3)
                self.switch_screen('home')
                self.update_resource_after_login()
                self.root.ids['sidebar_g'].raised=False
                
            else:
                Logger.info('Bad passwdord or username.')
        myThread(f, [None],dont_join=1)
        
    def login(self):
        self.switch_screen('login')
        
    def logout(self):
        self.spider.logout()
##        self.clear_conf()
        self.login()
        
    def clear_conf(self):
        for f in os.listdir(conf_dir):
            os.remove(os.path.join(conf_dir,f))
            
    def download_resource(self,url,filename, binary=True):
        Logger.info('DownLoading %s'%filename)
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
            self._update_canvas(l, i==length-1)

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
    def _update_canvas(self, id_, rename_now):
        self.root.ids[id_].canvas.ask_update()

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

    def add_songs_from_playlist(self,playlist_id,
                                screen_name='music_list',glayout_name='playlist_songs'):
        if type(playlist_id)==str:
            if playlist_id=='0000':
                pl_detail=(File.load_from_json(f) for f in self.get_all_cached_song_path())
            else:
                pl_path=self.get_pl_detail_path_by_id(playlist_id)
                if not os.path.exists(pl_path):
                    File.save_to_json(self.spider.playlist_detail(playlist_id),pl_path)

                pl_detail=File.load_from_json(pl_path)
        
        else:
            self.clear_glayout(glayout_name)
            pl_detail=playlist_id
            self.root.ids[glayout_name].current_playlist=pl_detail

        layout=self.root.ids.m_l_sv if self.root.current=='music_list' else self.root.ids.search_m_l_sv
        step=10
        pl_detail=list(pl_detail)
        for index in range(0, len(pl_detail), step):
            for i,song in enumerate(pl_detail[index:index+step], start=index):
                if self.root.current != screen_name:
                    return
                try:
                    author_name=(song.get('ar') or song['artists'])[0]['name'] 
                    self.add_layout(1,glayout_name,
                                    d_info=song,
                                    n0=str(i+1),
                                    t0=song['name'][:23],
                                    t1=author_name[:23],
                                    )
                except Exception as e:
                    Logger.info(e)
                    
            if index==10:
                time.sleep(.2)

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
##            breakpoint()

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
        Logger.info('Lock Acquired.')
        # Player Monitor
        if not self.player_monitor_actived :
            self.player_monitor_actived=True
            myThread(self.song_player_moniter,[None], dont_join=1)
            
        self.update_label_text('playbar_song_name',song['name'])
        self.update_image_source('playbar_status','src/playing.png')
        
        # if not android
        if not self.is_android:
            @mainthread
            def f():
                if self.current_song:
                    if self.playing_song['id'] != song['id'] and self.current_song.player:
                        self.current_song.stop()
                        self.current_song.unload()

                else:
                    self.root.ids['playbar'].height=self.root.height*.07

            f()
        else:
            if not self.played_on_android:
                @mainthread
                def f():
                    self.root.ids['playbar'].height=self.root.height*.07
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
                self.update_image_source('playbar_status', 'src/pausing.png')
                time.sleep(1)
                
                return myThread(self.play_a_new_song, [self.next_elem(song, self.playing_music_list)], dont_join=True)
            
            self.download_resource(url,song_path)

            # record to cached
            File.save_to_json(song,self.get_song_preview_path_by_id(song['id']))
            

        # if not android
        if not self.is_android:
            @mainthread
            def f():
                if self.playing_song['id'] != song['id'] or not self.current_song.player:
                    self.current_song=SoundLoader.load(song_path)
                    self.current_song.volume=self.default_volume
                    
                self.current_song.play()
                self.current_song.seek(0)

                self.playing_song=song
                
                self.lock=False
                Logger.info('Lock Release.')
                
            f()
            
        else:
            if self.playing_song['id'] != song['id']:
                self.player.setDataSource(song_path)
                
            self.player.prepare()
            self.player.start()
            self.player.seekTo(0)

            self.playing_song=song
            
            self.lock=False
            Logger.info('Lock Release.')


        # update the music cover image of playbar
        music_cover_path=self.get_music_cover_path_by_id(song['id'])

        if not os.path.exists(music_cover_path):
            cover_url=song['al']['picUrl'] if song.get('al') else song['album']['artist']['img1v1Url']
            self.download_resource(cover_url, music_cover_path)

        self.update_image_source('current_song_cover', music_cover_path)

    def song_player_moniter(self):
        while True:
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
##            self.play_a_new_song(self.next_elem(self.playing_song, self.playing_music_list))
        
        elif option_code==2:
            myThread(self.play_a_new_song, [choice(self.playing_music_list)], dont_join=True)
##            self.play_a_new_song(choice(self.playing_music_list))
 
    @mainthread
    def play_or_stop_current_song(self):
        layout=self.root.ids['playbar_status']
        layout.source = 'src/playing.png' if 'pausing.png' in layout.source else 'src/pausing.png'
        # if not android
        if not self.is_android:
            if self.current_song:
                if self.current_song.player:
                    if self.current_song.state=='stop':
                        self.current_song.play()
                        self.current_song.seek(self.music_pre_pos)
                        self.pausing=False
                          
                    else:
                        self.music_pre_pos=self.current_song.get_pos()
                        self.current_song.stop()
                        self.pausing=True
                else:
                    layout.source = 'src/pausing.png'
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
        
        if self.root.get_screen('music_list').current_pl_id==pl_id and pl_id!='0000':
            return

        pl_path=self.get_pl_preview_path_by_id(pl_id)
        
        if pl_id=='0000' and not os.path.exists(pl_path):
            pl={'creator': self.nickname,
                'id': '0000',
                'name':'缓存的音乐',
                'coverImgUrl':'src/avatar.jpg',
                'creator_id': self.id,
                'classify': 2}
            File.save_to_json(pl,pl_path)
            
        else:
            pl=File.load_from_json(pl_path)
            
        self.update_label_text('creator_name', pl['creator'])
        self.update_label_text('pl_name', pl['name'])
        self.update_image_source('big_pl_cover',self.get_pl_cover_by_id(pl_id))

        creator_img= self.get_user_cover_by_id(pl['creator_id'])
        
        if not os.path.exists(creator_img):
            self.download_resource(pl['creator_img'], creator_img)
            
        self.update_image_source('creator_avatar', creator_img)

        self.clear_glayout('playlist_songs')
        
        @mainthread
        def f():
            myThread(self.add_songs_from_playlist, [pl_id], dont_join=1)
            self.root.get_screen('music_list').current_pl_id=pl_id
        f()
        
        
    def smooth_slide_hori(self, id_, from_, to, total_time=.08, callback=None):
        if from_==to:return
        
        layout=self.root.ids[id_]
        process_n=20
        time_inter=total_time/process_n

        step=(to-from_)//process_n
        
        for x in range(from_,to,step):
            self.move_widget_pos(id_,[x,0])
            time.sleep(time_inter)

        self.move_widget_pos(id_, [to,0])
    
        if callback:
            @mainthread
            def f():
                callback()
            f()

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
    
    def touch_on_layout(self, args, do_this_anyway=None):
        instance, value = args
        if do_this_anyway or instance.collide_point(*value.pos):
            idd=instance.idd if not do_this_anyway else do_this_anyway
            
            layout=self.root.ids.sidebar_g
            if not do_this_anyway:
                if layout.raised and idd not in  \
                   ('menu','check_in', 'message','vip',
                    'ticket','shop','theme',
                    'night','setting',
                    'exit',):
                    return True

                if instance.to_window(*value.pos)[1]<self.playbar.height and \
                   idd not in ('play_or_stop', 'change_loop_status', 'song_detail'):
                    return

            if idd=='menu':
                layout=self.root.ids['sidebar_g']
                width=self.root.width

                from_,to = ([0,-1*width] if layout.raised else [-1*width,0] )
                def on_c(*_):
                    layout.raised=not layout.raised
                    if layout.raised:self.root.ids['shadow'].opacity=.4
                
                def on_s(*_):
                    if not layout.raised:
                        if not self.root.ids['sidebar_g'].width:
                            self.root.ids['sidebar_g'].width=self.root.width
                        
                        if self.playbar.height:
                            self.playbar.height=0

                    self.root.ids['shadow'].opacity=0

                anim = Factory.Animation(x=to, duration=.2, t='out_cubic') # + Animation(size=(80, 80), duration=2.)
                anim.on_start=on_s
                anim.on_complete=on_c
                anim.start(layout)
                
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
                
            elif idd=='back':
                self.switch_screen('home')
                
            elif idd=='recommand':
                self.move_mark_line(0)
                self.switch_glayout(1,0)
                
            elif idd=='friend':
                self.move_mark_line(1)
                self.switch_glayout(1,1)
                
            elif idd=='radio':
                self.move_mark_line(2)
                self.switch_glayout(1,2)


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
                layout=self.root.ids.sidebar_left_label
                layout.text='你不需要'

            elif idd=='setting':
                layout=self.root.ids.sidebar_left_label
                layout.text='设置啥'

            elif idd=='exit':
                self.logout()

            elif idd=='music_list':
                if 0 and instance.children[0].collide_point(*value.pos):
                    Logger.info('Setting')
                    
                else:
##                    breakpoint()
                    myThread(self.switch_to_music_list,[instance.playlist_id],dont_join=1)

            elif idd=='created_m_l_m':
                layout=self.root.ids.created
                
                l_height=self.root.height*.1
                for l in layout.children:
                    l.height = (l_height if l.height==0 else 0)

                layout=self.root.ids.created_m_l_m # Note: layout changed!
                layout_point_img=layout.children[0].children[-1].children[1]
                img_point='src/down.png' if 'right.png' in layout_point_img.source \
                           else 'src/right.png'
                self.update_image_source(layout_point_img,img_point)
                    
            elif idd=='collected_m_l_m':
                layout=self.root.ids.collected
                
                l_height=self.root.height*.1
                for l in layout.children:
                    l.height = (l_height if l.height==0 else 0)

                layout=self.root.ids.collected_m_l_m # Note: layout changed!
                layout_point_img=layout.children[0].children[-1].children[1]
                img_point='src/down.png' if 'right.png' in layout_point_img.source \
                           else 'src/right.png'
                self.update_image_source(layout_point_img,img_point)
                
                    
            elif idd=='play_or_stop':
                self.play_or_stop_current_song()

            elif idd=='song':
                if self.root.current=='music_list':
                    m_l_id=self.root.get_screen('music_list').current_pl_id
                    if m_l_id != self.playing_music_list_id:
                        self.playing_music_list_id=m_l_id
                        self.playing_music_list=self.get_pl_detail_by_id(m_l_id)
                elif self.root.current=='search':
                    self.playing_music_list=self.root.ids['search_pl_g'].current_playlist
                    
                myThread(self.play_a_new_song,[instance.d_info],dont_join=1)

            elif idd=='search_music':
                key_word=self.root.ids['search_bar'].text or self.root.ids['search_bar'].hint_text
                myThread(self.do_search,[key_word],dont_join=1)

            elif idd=='play_all_search_songs':
                self.playing_music_list=self.root.ids['search_pl_g'].current_playlist
                myThread(self.play_a_new_song,[self.playing_music_list[0]],dont_join=1)

            elif idd=='change_loop_status':
                self.loop_status = self.next_elem(self.loop_status, self.total_loop_kind)
                Logger.info(self.loop_status)

            elif idd=='song_detail':
                # detect children's task
                children_ids=['playbar_status', 'loop_stt',]
                for c in children_ids:
                    if self.root.ids[c].collide_point(*value.pos):
                        return
                
                self.switch_screen('song_lyric', move_playbar=False)
                
                song_lyric_path=self.get_song_lyric_path_by_id(self.playing_song['id'])
                if not os.path.exists(song_lyric_path):
                    song_lyric=self.spider.song_lyric(self.playing_song['id'])
                    File.save_to_json(song_lyric, song_lyric_path)
                    
                else:song_lyric=File.load_from_json(song_lyric_path)
                
                self.update_label_text('lyric_label', '\n'.join(song_lyric))
            
            return True

    def touch_scrllview(self, args, touch_on=True):
        instance, value = args
        if not self.player_monitor_actived or self.root.ids['common_box'].collide_point(*value.pos):
            return True
        
        if instance.collide_point(*value.pos):
            if touch_on:
                self.current_sv_pos= value.pos[1]
                
            else:
                dis=self.current_sv_pos-value.pos[1]
                if dis<-10:
                    if self.playbar.height:self.playbar.height=0
                elif dis>10:
                    if self.playbar.height==0:self.playbar.height=self.root.height*.07

            return True

    @mainthread
    def switch_screen(self, screen_name, move_playbar=True):
        if screen_name=='home':
            layout=self.root.ids['sidebar_g']
            if layout.width:layout.width=0

        if move_playbar:
            self.playbar.parent.remove_widget(self.playbar)
            layout=self.root.get_screen(screen_name)
            layout.add_widget(self.playbar)

        self.root.current=screen_name

    def switch_glayout(self,screen_widget_index=None,layout_index=None):
        if screen_widget_index != None:
            screen_widget_list=['first_page_s','second_page_glayout','third_page_s']
            
            for x in range(screen_widget_index):
                layout=self.root.ids[screen_widget_list[x]]
                layout.width=0

            layout=self.root.ids[screen_widget_list[screen_widget_index]]
            layout.width=self.root.width

        if layout_index != None:
            if screen_widget_index==1:
                layout_list=['first_page_2_s','second_page_2_s','third_page_2_s']
                
            elif screen_widget_index==2:
                layout_list=[]

            for x in range(layout_index):
                layout=self.root.ids[layout_list[x]]
                layout.width=0
                
            layout=self.root.ids[layout_list[layout_index]]
            layout.width=self.root.width

    def move_mark_line(self,pos_index):
        x_pos_list=[1/6, .5, 5/6]
        l=self.root.ids.w_u_l
        l.pos_hint={'center_x': x_pos_list[pos_index], 'center_y':l.pos_hint['center_y']}


if __name__ == '__main__':
    from kivy.config import Config
    from kivy.core.window import Window

    if kivy.platform != 'linux':
        # remove all breakpoints even if i forgot it,  ( ~>-<~ )
        breakpoint=lambda:None
        
##        Config.set('kivy', 'log_level', 'critical')
    
    LabelBase.register(name='kai', fn_regular='src/kai.ttf', fn_bold='src/kai.ttf')
    
    NetEaseApp().run()
