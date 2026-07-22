import { contextBridge } from 'electron';

contextBridge.exposeInMainWorld('avas', {
  electronVersion: process.versions.electron,
});
