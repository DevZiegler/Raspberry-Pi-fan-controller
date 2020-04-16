//based on "https://raspberrypi.stackexchange.com/a/92797" from Milliways (answered Jan 8 '19 at 3:27)
#include <lxpanel/plugin.h>

#include <stdio.h>

#define LabelSize 32

// in ms
#define FREQUENCY 1000
#define PATH "/home/pi/Raspberry-Pi-fan-controller/rpm"

static gboolean update_text (GtkWidget *label);

GtkWidget *test_constructor(LXPanel *panel, config_setting_t *settings)
{
 /* panel is a pointer to the panel and
     settings is a pointer to the configuration data
     since we don't use it, we'll make sure it doesn't
     give us an error at compilation time */
 (void)panel;
 (void)settings;

 // make a label out of the data
 char cIdBuf[LabelSize+1] = {'\0'};
 FILE *fp;
 fp = fopen(PATH, "r");
 fgets(cIdBuf, LabelSize, fp);
 fclose(fp);

 // create a label widget instance
 GtkWidget *pLabel = gtk_label_new(cIdBuf);
 

 
 // set the label to be visible
 gtk_widget_show(pLabel);

 // need to create a container to be able to set a border
 GtkWidget *p = gtk_event_box_new();

 // our widget doesn't have a window...
 // it is usually illegal to call gtk_widget_set_has_window() from application but for GtkEventBox it doesn't hurt
 gtk_widget_set_has_window(p, FALSE);

 // set border width
 gtk_container_set_border_width(GTK_CONTAINER(p), 1);

 // add the label to the container
 gtk_container_add(GTK_CONTAINER(p), pLabel);

 // set the size we want
 // gtk_widget_set_size_request(p, 100, 25);
 
 
 g_timeout_add (FREQUENCY, (GSourceFunc)update_text, pLabel);
 //gtk_label_set_text(GTK_LABEL (pLabel), "test1");
 
 // success!!!
 return p;
}

static gboolean update_text (GtkWidget *label)
{ 
 /* A prettier solution would proably be to remove the timeout when
 * the window is closed */
 if (GTK_IS_LABEL(label))
 {
  char cIdBuf[LabelSize+1] = {'\0'};
  FILE *fp;
  fp = fopen(PATH, "r");
  fgets(cIdBuf, LabelSize, fp);
  fclose(fp);
  
  gtk_label_set_text (GTK_LABEL(label), cIdBuf);
  return TRUE;
 }
 /* Returning FALSE removes the timeout from the glib main loop */
 else
  return FALSE;

}

FM_DEFINE_MODULE(lxpanel_gtk, test)

/* Plugin descriptor. */
LXPanelPluginInit fm_module_init_lxpanel_gtk = {
   .name = "Fan Controller - RPM",
   .description = "Display RPM from fan controller",
   .one_per_system = 1,

   // assigning our functions to provided pointers.
   .new_instance = test_constructor
};
