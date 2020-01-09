import sys
sys.path.append('./NEMbox')

import os
import re
import time
from copy import deepcopy as dc
from functools import reduce
from datetime import datetime

import api

from mythread import myThread
from dialy import save_to_file, save_to_json, load_from_json
from myspider import Spider

import kivy
from kivy.app import App
from kivy.clock import Clock
from kivy.clock import mainthread
from kivy.core.text import LabelBase
from kivy.factory import Factory
from kivy.core.audio import SoundLoader


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
        self.conf_dir='NEMbox/.netease-musicbox'
        if not os.path.exists(self.conf_dir):
            os.mkdir(self.conf_dir)
            
        if not os.path.exists(self.conf_dir):
            os.mkdir(self.conf_dir)
            
        self.user_info_path='NEMbox/.netease-musicbox/user_info.json'
        self.user_playlist_path='NEMbox/.netease-musicbox/user_playlist.json'
        
        self.pl_head='p_c_'
        
        self.avatar_fn='src/avatar.jpg'
        self.avatar_id_list=['avatar_image_0','avatar_image_1']
        self.nickname_id_list=['avatar_text_0','avatar_text_1']

        self.current_song=None
        self.default_volume=.01
        self.music_pre_pos=None

        self.played_on_android=False
        # if android
        if kivy.platform == 'android':
            self.is_android=True
            
            from jnius import autoclass
            MediaPlayer = autoclass('android.media.MediaPlayer')
            self.player = MediaPlayer()

        else:
            self.is_android=False

        self.removed_widget_dict={}
        
    def load_user_info(self,):
        
        if not os.path.exists(self.user_info_path):
            ori_info={
                'profile':{'nickname':'游客'},
                      }
            save_to_json(ori_info ,self.user_info_path)
            
        self.user_info=load_from_json(self.user_info_path)
        self.nickname=self.user_info['profile']['nickname']
        
    def init_kivy_conf(self,):
        self.font_size=25 if kivy.platform == 'linux' else 40
        self.width,self.height =Window.size
        
    def _init(self,):
        self.spider=api.NetEase()

    def touch_on_android_button(self, window, key, *args):
        if key==27:
##            self.update_label_text('sidebar_left_label',str(key))
            if self.root.ids['sidebar_g'].raised:self.touch_on_layout([None]*2,'menu')
            
            if self.root.current != 'home':
                self.switch_screen('home')
            else:
                pass
            
            return True
        

    def get_pl_cover_by_id(self,id_):
        if id_=='0000':return 'src/cached_pl_cover.png'
        return os.path.join(self.conf_dir ,self.pl_head+str(id_)+'.jpg')

    def get_user_cover_by_id(self, id_):
        return os.path.join(self.conf_dir ,self.pl_head+'c_'+str(id_)+'.jpg')

    def get_music_path_by_id(self, id_):
        return os.path.join(self.conf_dir ,self.pl_head+'m_'+str(id_)+'.mp3')

    def get_music_cover_path_by_id(self, id_):
        return os.path.join(self.conf_dir ,self.pl_head+'m_'+str(id_)+'.jpg')

    def get_pl_detail_path_by_id(self, id_):
        return os.path.join(self.conf_dir ,self.pl_head+'d_'+str(id_)+'.json')

    def get_last_date_path(self):
        return os.path.join(self.conf_dir ,'last_date.json')

    def get_daily_rec_playlists(self):
        return os.path.join(self.conf_dir ,'daily_rec_playlists.json')
    
    def login_by_pd(self):
        def f():
            username=self.root.ids.t_i_un.text
            passwd=self.root.ids.t_i_pd.text
            if self.spider.login(username, passwd, need_md5_enc=1):
                print('Login Successful !')
                time.sleep(.3)
                self.switch_screen('home')
                self.update_resource_after_login()
                self.touch_on_layout([None]*2,'menu')
                
            else:
                print('Bad passwdord or username !')
        myThread(f, [None],dont_join=1)
        
    def login(self):
        self.switch_screen('login')
        
    def logout(self):
        self.spider.logout()
##        self.clear_conf()
        self.login()
        
    def clear_conf(self):
        for f in os.listdir(self.conf_dir):
            os.remove(os.path.join(self.conf_dir,f))
            
    def download_resource(self,url,filename, binary=True):
        print('DownLoad %s'%filename)
        r=Spider(url).get()
        if binary:save_to_file(r.content, filename)
        else: save_to_file(r.text, filename)
        
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
        if need_dowload: self.download_resource(url,self.avatar_fn+'tem.jpg')

        length=len(avater_id_list)
        for i,l in enumerate(avater_id_list):
            self._update_canvas(l, i==length-1)

    @mainthread
    def update_image_source(self,id_, new_source=None):
        layout=self.root.ids[id_] if type(id_)==str else id_
        if new_source:layout.source=new_source
        return 
##        layout.reload()

    @mainthread
    def update_label_text(self, id_, text, layout_type=0):
        if layout_type==0:
            layout=self.root.ids[id_]
        elif layout_type==1:
            layout=self.root.ids[id_]
        layout.text=text

    @mainthread
    def _update_canvas(self, id_, rename_now):
        layout=self.root.ids[id_].canvas.before.children[1]
        
        # reload
        layout.source=self.avatar_fn+'tem.jpg'
        
        if rename_now:
            os.rename(self.avatar_fn+'tem.jpg', self.avatar_fn)
        
    def api_event_listener(self):
        while 1:
            got=api.q_put.get(None)
            
            if got=='input_un_pd':
                self.login()

    def update_user_playlist(self, only_from_local_file=False):
        if os.path.exists(self.user_playlist_path):
            playlist=load_from_json(self.user_playlist_path)
            
        elif not only_from_local_file:
            playlist=self.parse_playlist()
            
            


        self.playlist=playlist
        self._update_user_playlist(playlist)

    def get_playlist_by_id(self,id_):
        #reduce(lambda x,y:self.playlist[x]+self.playlist[y],self.playlist.keys())
        for pl in self.playlist['created']+self.playlist['collected']+self.playlist['cached']: 
            if pl['id']== id_:return pl
            
    def _update_user_playlist(self, playlist):
        self.clear_glayout('created')
        self.clear_glayout('collected')

        @mainthread
        def f():
            layout=self.root.ids['created_m_l_m']
            layout.t0=re.sub('\d+',str(len(playlist['created'])),layout.t0)
            
            layout=self.root.ids['collected_m_l_m']
            layout.t0=re.sub('\d+',str(len(playlist['collected'])),layout.t0)

        f()
        myThread(self.add_single_playlist,
                 list(zip(playlist['created'], ['created']*len(playlist['created']))), dont_join=1)
        
        myThread(self.add_single_playlist,
                 list(zip(playlist['collected'], ['collected']*len(playlist['collected']))), dont_join=1)

    def add_single_playlist(self, playlist, parent, type_=0):
        if type_==0:
            id_,img,name,creator= [playlist[x] for x in ['id','coverImgUrl','name','creator']]
            t1='0首 by %s'%creator
            
        elif type_==1:
            id_,img,name= [playlist[x] for x in ['id','picUrl','name']]
        
            
        img_fn=self.get_pl_cover_by_id(id_)
        
        if not os.path.exists(img_fn):self.download_resource(img,img_fn)

        if type_==0:
            self.add_layout(0,parent,t0=name,t1=t1,i0=img_fn, playlist_id=id_)
        elif type_==1:
            self.add_layout(2,parent,s0=img_fn,t0=name,playlist_id=str(id_))

    def add_songs_from_playlist(self,playlist_id,
                                screen_name='music_list',glayout_name='playlist_songs'):
        if type(playlist_id)==str:
            pl_path=self.get_pl_detail_path_by_id(playlist_id)
            if not os.path.exists(pl_path):
                save_to_json(self.spider.playlist_detail(playlist_id),pl_path)

            pl_detail=load_from_json(pl_path)
        
        else:
            self.clear_glayout(glayout_name)
            pl_detail=playlist_id

        
        for i,song in enumerate(pl_detail):
            if self.root.current != screen_name:
                break
            try:
                author_name=(song.get('ar') or song['artists'])[0]['name'] 
                self.add_layout(1,glayout_name,
                                d_info=song,
                                n0=str(i+1),
                                t0=song['name'],
                                t1=author_name,
                                )
            except Exception as e:
                print(e)

    
    @mainthread
    def add_layout(self, layout_type, parent, *unuse,**kw):
        if layout_type==0:
            l=Factory.PlaylistGlayout
            
        elif layout_type==1:
            l=Factory.SingleMusicGlayout

        elif layout_type==2:
            l=Factory.RecommendPlaylist
        
        self.root.ids[parent].add_widget(l(**kw))
        
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
        self.update_label_text('playbar_song_name',song['name'])
        self.update_image_source('playbar_status','src/playing.png')
        
        # if not android
        if not self.is_android:
            @mainthread
            def f():
                if self.current_song:
                    self.current_song.stop()
                    self.current_song.unload()
                    
                else:
                    self.root.ids['playbar'].height=self.root.height*.07

            f()
        else:
            if self.root.ids['playbar'].height==0:
                self.root.ids['playbar'].height=self.root.height*.07
                self.played_on_android=True
                
            self.player.reset()
            
        song_path=self.get_music_path_by_id(song['id'])
        
        if not os.path.exists(song_path):
            url=self.spider.songs_url([song['id']])[0]['url']
            if not url:
                self.update_label_text('playbar_song_name','抱歉，无法播放该音乐')
                self.update_image_source('playbar_status','src/pausing.png')
                return
            
            self.download_resource(url,song_path)

            # record to cached
            cached_pl_path=self.get_pl_detail_path_by_id('0000')
            if not os.path.exists(cached_pl_path):
                cached_songs=[]
            else:
                cached_songs=load_from_json(cached_pl_path)
                
            cached_songs.append(song)
            save_to_json(cached_songs,cached_pl_path)
            

        # if not android
        if not self.is_android:
            @mainthread
            def f():
                self.current_song=SoundLoader.load(song_path)
                self.current_song.volume=self.default_volume
                self.current_song.play()
            f()
            
        else:
            self.player.setDataSource(song_path)
            self.player.prepare()
            self.player.start()

        # update the music cover image of playbar
        music_cover_path=self.get_music_cover_path_by_id(song['id'])

        if not os.path.exists(music_cover_path):
            cover_url=song['al']['picUrl'] if song.get('al') else song['album']['artist']['img1v1Url']
            self.download_resource(cover_url, music_cover_path)

        self.update_image_source('current_song_cover', music_cover_path)
    
    @mainthread
    def play_or_stop_current_song(self):
        layout=self.root.ids['playbar_status']
        layout.source = 'src/playing.png' if 'pausing.png' in layout.source else 'src/pausing.png'
        # if not android
        if not self.is_android:
            if self.current_song:
                if self.current_song.state=='stop':
                    self.current_song.play()
                    self.current_song.seek(self.music_pre_pos)
                      
                else:
                    self.music_pre_pos=self.current_song.get_pos()
                    self.current_song.stop()

        else:
            if self.player.isPlaying():
                self.player.pause()
            else:
                self.player.start()

    
    def parse_playlist(self):
        playlist=self.spider.user_playlist()
        user_playlist={'created':[], 'collected':[], 'cached':[]}
        
        for pl in playlist:
            info={'creator':pl['creator']['nickname'],
                  'id': str(pl['id']),
                  'name': pl['name'],
                  'coverImgUrl': pl.get('coverImgUrl') or pl['picUrl'],
                  'creator_img': pl['creator']['avatarUrl'],
                  'creator_id': str(pl['creator']['userId']),
                  }
            
            if pl['creator']['userType'] == 0:
                user_playlist['created'].append(info)
            else:
                user_playlist['collected'].append(info)

        user_playlist['cached'] =  [dc(user_playlist['created'][0])]
        user_playlist['cached'][0].update({'name':'自动缓存音乐','id':'0000'})

        
##        self.playlist=user_playlist
        save_to_json(user_playlist, self.user_playlist_path)

        return user_playlist

    def switch_to_music_list(self,pl_id):
        self.switch_screen('music_list')
        
        if self.root.get_screen('music_list').current_pl_id==pl_id:
            return
        
        pl=self.get_playlist_by_id(pl_id)
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
        search_result_songs=self.spider.search(key_word)['songs']
        self.add_songs_from_playlist(search_result_songs,'search','search_pl_g')
        
    def update_daily_recommend_pl(self):
        _now=datetime.now()
        now=[_now.year,_now.month,_now.day]

        date_path=self.get_last_date_path()
        
        if not os.path.exists(date_path):
            last_date=[]
            save_to_json(now,date_path)
        else:
            last_date=load_from_json(date_path)

        if last_date != now:
            rec_pl=self.spider.recommend_resource()
            save_to_json(rec_pl,self.get_daily_rec_playlists())
            save_to_json(now,date_path)

        else:
            rec_pl=load_from_json(self.get_daily_rec_playlists())
            
        for pl in rec_pl:
            self.add_single_playlist(pl,'recommand_m_l',type_=1)
    
    def touch_on_layout(self, args, do_this_anyway=None):
        instance, value = args
        if do_this_anyway or instance.collide_point(*value.pos):
            idd=instance.idd if not do_this_anyway else do_this_anyway

            layout=self.root.ids.sidebar_g
            if layout.pos[0] != -1*layout.width and idd not in  \
               ('menu','check_in', 'message','vip','ticket','shop','night','setting','exit',):
                return True
            
            
            if idd=='menu':
                def f(callbk=True):
                    layout=self.root.ids['shadow']
                    layout.opacity=(0 if layout.opacity else .4)

                    layout=self.root.ids['sidebar_g']
                    if callbk:
                        layout.raised=not layout.raised
                        
                    if not callbk and not layout.raised:
                        self.playbar.height=0

                    elif callbk and (self.current_song or self.played_on_android) and not layout.raised:
                        self.playbar.height=self.root.height*.07
                    
                f(False)
                layout=self.root.ids['sidebar_g']
                if not layout.raised:
                    layout.width=Window.size[0]
                    
                from_,to = ([0,-1*layout.width] if layout.pos[0]==0 else [-1*layout.width,0] )
                myThread(lambda :self.smooth_slide_hori('sidebar_g', from_, to,callback=f), [None],dont_join=1 )
                
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

            elif idd=='night':
                layout=self.root.ids.sidebar_left_label
                layout.text='你不需要'

            elif idd=='setting':
                layout=self.root.ids.sidebar_left_label
                layout.text='设置啥'

            elif idd=='exit':
##                layout=self.root.ids.sidebar_left_label
##                layout.text='滚滚滚'
##                sys.exit(0)
##                exit(0)
                self.logout()
                
            elif idd=='music_list':
                if 0 and instance.children[0].collide_point(*value.pos):
                    print('Setting')
                    
                else:
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
                myThread(self.play_a_new_song,[instance.d_info],dont_join=1)

            elif idd=='search_music':
                key_word=self.root.ids['search_bar'].text
                myThread(self.do_search,[key_word],dont_join=1)
            return True

    @mainthread
    def switch_screen(self, screen_name):
##        if screen_name=='home':
##            layout=self.root.ids['sidebar_g']
##            if layout.width:layout.width=0
            
        self.root.current=screen_name

##        self.playbar.parent.remove_widget(self.playbar)
##        layout=self.root.get_screen(screen_name).children[-1]
##        layout.add_widget(self.playbar)

        
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
        Config.set('kivy', 'log_level', 'critical')
    
    LabelBase.register(name='kai', fn_regular='src/kai.ttf', fn_bold='src/kai.ttf')
    NetEaseApp().run()
