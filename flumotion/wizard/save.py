from flumotion.wizard.enums import *

video_source_components = { VideoDevice.TVCard    : 'tv-card',
                            VideoDevice.Firewire  : 'firewire',
                            VideoDevice.Webcam    : 'webcam',
                            VideoDevice.Test      : 'videotestsrc' }
audio_source_components = { AudioDevice.Firewire  : 'audio-firewire',
                            AudioDevice.Soundcard : 'alsasrc',
                            AudioDevice.Test      : 'sinesrc' }

class Component:
    def __init__(self, name, type, properties={}):
        self.name = name
        self.type = type
        self.props = properties
        self.eaters = []
        self.feeders = []
        
    def __repr__(self):
        return '<flumotion.wizard.save.Component name="%s">' % self.name

    def addEater(self, component):
        self.eaters.append(component)
        
    def addFeeder(self, component):
        self.feeders.append(component)

    def link(self, component):
        self.feeders.append(component)
        component.addEater(self)
        
    def toXML(self):
        s = '    <component name="%s" type="%s">\n' % (self.name, self.type)

        # XXX: Handle eaters properly
        s += '      <feed>default</feed>\n'
                
        for source in self.feeders:
            s += "      <source>%s</source>\n" % source.name

        if self.props:
            s += "      <!-- properties -->\n"
            property_names = self.props.keys()
            property_names.sort()
            
            for name in property_names:
                value = self.props[name]
                s += "      <%s>%s</%s>\n" % (name, value, name)
            
        s += "    </component>\n"
        return s
    
    def printTree(self, indent=1):
        print indent * '*', self.name, self.type, \
              tuple([f.name for f in self.feeders]) or ''
        for eater in self.eaters:
            eater.printTree(indent+1)
            
class WizardSaver:
    def __init__(self, wizard):
        self.wizard = wizard

    def getVideoSource(self):
        options = self.wizard.get_step_options('Source')
        source = options['video']
        video_step = self.wizard[source.step]
        return Component('video-source', source.component_type,
                         video_step.get_component_properties())

    def getVideoOverlay(self, show_logo):
        # At this point we already know that we should overlay something
        step = self.wizard['Overlay']
        if show_logo:
            properties = step.get_component_properties()
            properties['fluendo_logo'] = True
            encoding_options = self.wizard.get_step_options('Encoding')
            if (encoding_options['format'] == EncodingFormat.Ogg or
                encoding_options['video'] == EncodingVideo.Theora):
                properties['xiph_logo'] = True

            license_options = self.wizard.get_step_options('Content License')
            if license_options['license'] == LicenseType.CC:
                properties['cc_logo'] = True
    
        return Component('video-overlay', 'overlay', properties)
        
    def getVideoEncoder(self):
        options = self.wizard.get_step_options('Encoding')
        encoder = options['video']
        encoder_step = self.wizard[encoder.step]
        return Component('video-encoder', encoder.component_type,
                         encoder_step.get_component_properties())

    def getAudioSource(self):
        options = self.wizard.get_step_options('Source')
        source = options['audio']
        if source == AudioDevice.Test:
            props = {}
        else:
            audio_step = self.wizard['Audio Source']
            props = audio_step.get_component_properties()
        
        return Component('audio-source', source.component_type, props)

    def getAudioEncoder(self):
        options = self.wizard.get_step_options('Encoding')
        encoder = options['audio']
        
        if encoder == EncodingAudio.Mulaw:
            props = {}
        else:
            encoder_step = self.wizard[encoder.step]
            props = encoder_step.get_component_properties()
            
        return Component('audio-encoder', encoder.component_type, props)

    def getMuxer(self, name):
        options = self.wizard.get_step_options('Encoding')
        muxer = options['format']
        return Component('multiplexer-' + name, muxer.component_type)

    def handleVideo(self, components):
        overlay_options = self.wizard.get_step_options('Overlay')
        has_overlay = overlay_options['show_logo'] or \
                      overlay_options['show_text']
        
        video_source =  self.getVideoSource()
        components.append(video_source)
            
        video_overlay = None
        video_encoder = self.getVideoEncoder()
            
        if has_overlay:
            video_overlay = self.getVideoOverlay(overlay_options['show_logo'])
            components.append(video_overlay)
                
        if video_overlay is not None:
            video_overlay.link(video_source)
            video_encoder.link(video_overlay)
        else:
            video_encoder.link(video_source)
        components.append(video_encoder)
        return video_encoder
            
    def handleAudio(self, components):
        audio_source = self.getAudioSource()
        components.append(audio_source)

        audio_encoder = self.getAudioEncoder()
        components.append(audio_encoder)
        audio_encoder.link(audio_source)

        return audio_encoder
    
    def handleConsumers(self, components, audio_encoder, video_encoder):
        cons_options = self.wizard.get_step_options('Consumption')
        has_audio = self.wizard.get_step_option('Source', 'has_audio')
        has_video = self.wizard.get_step_option('Source', 'has_video')

        audio_muxer = None
        if has_audio:
            audio_muxer = self.getMuxer('audio')
            components.append(audio_muxer)
            audio_muxer.link(audio_encoder)
            
        video_muxer = None
        if has_video:
            video_muxer = self.getMuxer('video')
            components.append(video_muxer)
            video_muxer.link(video_encoder)

        steps = []
        if has_audio and has_video:
            both_muxer = self.getMuxer('audio-video')
            components.append(both_muxer)
            both_muxer.link(video_encoder)
            both_muxer.link(audio_encoder)
            
            if cons_options['http']:
                if cons_options['http_audio_video']:
                    steps.append(('http_audio_video', 'http-audio-video',
                                  'http-streamer',
                                  'HTTP Streamer (audio & video)', both_muxer))
                if cons_options['http_audio']:
                    steps.append(('http_audio', 'http-audio', 'http-streamer',
                                  'HTTP Streamer (audio only)', audio_muxer))
                if cons_options['http_video']:
                    steps.append(('http_video', 'http-video', 'http-streamer',
                                  'HTTP Streamer (video only)', video_muxer))
            if cons_options['disk']:
                if cons_options['disk_audio_video']:
                    steps.append(('disk_audio_video', 'disk-audio-video',
                                  'file-dumper', 'Disk (audio & video)',
                                  both_muxer))
                if cons_options['disk_audio']:
                    steps.append(('disk_audio', 'disk-audio', 'file-dumper',
                                  'Disk (audio only)', audio_muxer))
                if cons_options['disk_video']:
                    steps.append(('disk_video', 'disk-video', 'file-dumper',
                                  'Disk (video only)', video_muxer))
        elif has_video and not has_audio:
            if cons_options['http']:
                steps.append(('http_video', 'http-video', 'http-streamer',
                              'HTTP Streamer (video only)', video_muxer))
            if cons_options['disk']:
                steps.append(('disk_video', 'disk-video', 'file-dumper',
                              'Disk (video only)', video_muxer))
        elif has_audio and not has_video:
            if cons_options['http']:
                steps.append(('http_audio', 'http-audio', 'http-streamer',
                              'HTTP Streamer (audio only)', audio_muxer))
            if cons_options['disk']:
                steps.append(('disk_audio', 'disk-audio', 'file-dumper',
                              'Disk (audio only)', audio_muxer))
        else:
            raise AssertionError

        for key, name, type, step_name, muxer in steps:
            if not cons_options.has_key(key):
                continue
            step = self.wizard[step_name]
            consumer = Component(name, type, step.get_component_properties())
            consumer.link(muxer)
            components.append(consumer)

        if not audio_muxer.eaters:
            components.remove(audio_muxer)
        if not video_muxer.eaters:
            components.remove(video_muxer)
        if not both_muxer.eaters:
            components.remove(both_muxer)
            
    def getXML(self):
        source_options = self.wizard.get_step_options('Source')
        has_video = source_options['has_video']
        has_audio = source_options['has_audio']

        components = []
        
        audio_encoder = None
        if has_audio:
            audio_encoder = self.handleAudio(components)
            
        video_encoder = None
        if has_video:
            video_encoder = self.handleVideo(components)
            
        self.handleConsumers(components, audio_encoder, video_encoder)
        
        s = '<planet>\n'
        s += '  <atmosphere>\n'
        for component in components:
            s += component.toXML()
        s += '  </atmosphere>\n'
        s += '</planet>\n'

        return s

