using System;
using System.Collections.Generic;
using System.IO;
using System.Windows.Forms;
using System.Xml.Linq;

namespace MusicBeePlugin
{
    public partial class Form1 : Form
    {
        private Plugin.MusicBeeApiInterface mbApi;

        public Form1(Plugin.MusicBeeApiInterface api)
        {
            InitializeComponent();
            mbApi = api;
        }

        private void button1_Click(object sender, EventArgs e)
        {
            string pluginFolder = Path.GetDirectoryName(System.Reflection.Assembly.GetExecutingAssembly().Location);
            string xmlPath = Path.Combine(pluginFolder, "RekordBoxLibrary.xml");

            if (!File.Exists(xmlPath))
            {
                MessageBox.Show("XML file not found: " + xmlPath);
                return;
            }

            try
            {
                XDocument doc = XDocument.Load(xmlPath);

                // Step 1: Build a dictionary of TrackID -> file path
                var trackLookup = new Dictionary<string, string>();
                var collection = doc.Root.Element("COLLECTION");
                if (collection != null)
                {
                    foreach (var track in collection.Elements("TRACK"))
                    {
                        string trackId = track.Attribute("TrackID")?.Value;
                        string location = track.Attribute("Location")?.Value;
                        if (trackId != null && location != null)
                        {
                            string filePath = Uri.UnescapeDataString(
                                location.Replace("file://localhost/", "")
                            ).Replace("/", "\\");
                            trackLookup[trackId] = filePath;
                        }
                    }
                }

                // Step 2: Build lookup of existing MusicBee playlists once
                var existingPlaylists = BuildPlaylistLookup();

                // Step 3: Walk the playlist tree recursively
                var playlists = doc.Root.Element("PLAYLISTS");
                if (playlists != null)
                {
                    int created = 0;
                    int updated = 0;
                    foreach (var rootNode in playlists.Elements("NODE"))
                    {
                        ProcessNode(rootNode, "", trackLookup, existingPlaylists, ref created, ref updated);
                    }
                    MessageBox.Show($"Done! Created {created} new playlists, updated {updated} existing playlists.");
                }
                else
                {
                    MessageBox.Show("No PLAYLISTS section found in the XML.");
                }
            }
            catch (Exception ex)
            {
                MessageBox.Show("Error: " + ex.Message);
            }
        }

        private Dictionary<string, string> BuildPlaylistLookup()
        {
            var lookup = new Dictionary<string, string>(StringComparer.OrdinalIgnoreCase);
            if (mbApi.Playlist_QueryPlaylists())
            {
                string playlistUrl;
                while ((playlistUrl = mbApi.Playlist_QueryGetNextPlaylist()) != null)
                {
                    string name = mbApi.Playlist_GetName(playlistUrl);
                    lookup[playlistUrl] = name;
                }
            }
            return lookup;
        }

        private string FindPlaylist(string playlistName, string folderPath,
            Dictionary<string, string> existingPlaylists)
        {
            string expectedEnd = string.IsNullOrEmpty(folderPath)
                ? playlistName
                : folderPath + "\\" + playlistName;

            foreach (var kvp in existingPlaylists)
            {
                if (kvp.Value == expectedEnd)
                {
                    if (kvp.Key.EndsWith(expectedEnd + ".mbp", StringComparison.OrdinalIgnoreCase) ||
                        kvp.Key.EndsWith(expectedEnd.Replace("\\", "/"), StringComparison.OrdinalIgnoreCase))
                    {
                        return kvp.Key;
                    }
                }
            }
            return null;
        }

        private void ProcessNode(XElement node, string folderPath,
            Dictionary<string, string> trackLookup,
            Dictionary<string, string> existingPlaylists,
            ref int created, ref int updated)
        {
            string nodeType = node.Attribute("Type")?.Value;
            string nodeName = node.Attribute("Name")?.Value;

            if (nodeType == "0")
            {
                string newPath = string.IsNullOrEmpty(folderPath)
                    ? nodeName
                    : folderPath + "\\" + nodeName;

                foreach (var child in node.Elements("NODE"))
                {
                    ProcessNode(child, newPath, trackLookup, existingPlaylists, ref created, ref updated);
                }
            }
            else if (nodeType == "1")
            {
                var filePaths = new List<string>();
                foreach (var trackRef in node.Elements("TRACK"))
                {
                    string key = trackRef.Attribute("Key")?.Value;
                    if (key != null && trackLookup.ContainsKey(key))
                    {
                        filePaths.Add(trackLookup[key]);
                    }
                }

                if (filePaths.Count > 0)
                {
                    string existingUrl = FindPlaylist(nodeName, folderPath, existingPlaylists);

                    if (existingUrl != null)
                    {
                        mbApi.Playlist_SetFiles(existingUrl, filePaths.ToArray());
                        updated++;
                    }
                    else
                    {
                        mbApi.Playlist_CreatePlaylist(folderPath, nodeName, filePaths.ToArray());
                        created++;
                    }
                }
            }
        }
    }
}