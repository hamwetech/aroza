from django import forms
from activity.models import ThematicArea, TrainingSession, ExternalTrainer, TrainingTopic, TrainingContent
from conf.utils import bootstrapify



class ThematicAreaForm(forms.ModelForm):
    class Meta:
        model = ThematicArea
        fields = ['thematic_area', 'description']
        

class TrainingForm(forms.ModelForm):
    class Meta:
        model = TrainingSession
        exclude = ['create_date', 'update_date', 'created_by' , 'training_reference']
    
    def __init__(self, *args, **kwargs):
        super(TrainingForm, self).__init__(*args, **kwargs)
        self.fields['coop_member'].widget.attrs['id'] = 'selec_adv_1'
        

class ExternaTrainerForm(forms.ModelForm):
    class Meta:
        model = ExternalTrainer
        exclude = ['create_date', 'update_date']


class TrainingTopicForm(forms.ModelForm):
    class Meta:
        model = TrainingTopic
        exclude = ['create_date', 'update_date']
    

class TrainingContentForm(forms.ModelForm):
    class Meta:
        model = TrainingContent
        exclude = ['create_date', 'update_date', 'created_by', 'thematic_area']

    def __init__(self, *args, **kwargs):
        super(TrainingContentForm, self).__init__(*args, **kwargs)
        self.fields['content'].widget = forms.TextInput(attrs={
            'id': 'wysiwyg_tinymce',
            'data-parsley-trigger': 'keyup'
        })


bootstrapify(ExternaTrainerForm)
bootstrapify(ThematicAreaForm)
bootstrapify(TrainingForm)
bootstrapify(TrainingTopicForm)
bootstrapify(TrainingContentForm)