import React, { useState, useRef, useEffect } from 'react'
import { Play, Pause, Volume2, VolumeX, RotateCcw, Headphones, AlertCircle } from 'lucide-react'
import { Button } from './ui/button'

export const AudioPlayer: React.FC<{src?: string | null; title?: string}> = ({src,title}) => {
  const audio = useRef<HTMLAudioElement>(null)
  const [playing,setPlaying] = useState(false)
  const [duration,setDuration] = useState(0)
  const [time,setTime] = useState(0)
  const [muted,setMuted] = useState(false)
  const [speed,setSpeed] = useState(1)
  const [error,setError] = useState('')
  useEffect(() => {setPlaying(false);setDuration(0);setTime(0);setError('');setMuted(false);setSpeed(1)},[src])
  const format = (n: number) => `${Math.floor(n / 60)}:${String(Math.floor(n % 60)).padStart(2,'0')}`
  const toggle = async () => {
    if (!audio.current) return
    if (playing) audio.current.pause()
    else { try { await audio.current.play(); setError('') } catch {setError('This recording could not be played. Check the audio URL or try again.')} }
  }
  if (!src) return <div className="audio-empty"><Headphones size={22}/><div><strong>No recording attached</strong><p>Add an audio URL when logging a call to listen here.</p></div></div>
  return <div className="audio-player"><audio key={src} ref={audio} src={src} preload="metadata" onLoadedMetadata={() => setDuration(Number.isFinite(audio.current?.duration) ? audio.current!.duration : 0)} onTimeUpdate={() => setTime(audio.current?.currentTime || 0)} onPlay={() => setPlaying(true)} onPause={() => setPlaying(false)} onEnded={() => {setPlaying(false);setTime(0)}} onError={() => {setPlaying(false);setError('Recording unavailable. The audio URL may have expired.')}}/>
    <div className="audio-title"><Headphones size={17}/><strong>{title || 'Call recording'}</strong><span>{format(time)} / {format(duration)}</span></div>
    <div className="audio-controls"><Button size="icon" aria-label={playing ? 'Pause recording' : 'Play recording'} onClick={toggle}>{playing ? <Pause size={17}/> : <Play size={17}/>}</Button><input aria-label="Seek recording" type="range" min={0} max={duration || 1} step="0.1" value={time} disabled={!duration} onChange={e => {const value = Number(e.target.value); if (audio.current) audio.current.currentTime = value;setTime(value)}}/><Button variant="ghost" size="sm" aria-label={`Playback speed ${speed} times. Change speed`} onClick={() => {const speeds = [1,1.25,1.5,2];const next = speeds[(speeds.indexOf(speed)+1)%4];setSpeed(next);if(audio.current) audio.current.playbackRate = next}}>{speed}x</Button><Button variant="ghost" size="icon" aria-label="Restart recording" onClick={() => {if(audio.current) audio.current.currentTime=0;setTime(0)}}><RotateCcw size={16}/></Button><Button variant="ghost" size="icon" aria-label={muted ? 'Unmute recording' : 'Mute recording'} onClick={() => {if(audio.current) audio.current.muted=!muted;setMuted(!muted)}}>{muted ? <VolumeX size={16}/> : <Volume2 size={16}/>}</Button></div>
    {error && <p className="audio-error" role="alert"><AlertCircle size={16}/>{error}</p>}
  </div>
}
