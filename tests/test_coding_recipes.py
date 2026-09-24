from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'src'))
from jev_reflex import recipes
from jev_reflex.reflex import ReflexError


class CodingRecipes(unittest.TestCase):
    def test_tool_choices_are_allowlisted_and_never_execute(self):
        item = dict(id='a', privacy_namespace='p', text='Compiler cannot resolve a symbol.',
                    goal='Investigate the symbol.', eligible_tools=[
                        dict(option_id='search', description='Search supplied repository source.'),
                        dict(option_id='test', description='Run the existing test command when authorized.')])
        expanded = recipes.prepare('tool_advice/v1', 'p', True, [item])
        self.assertEqual(set(expanded[0]['choices']), {'search','test','no_tool','uncertain'})
        out = recipes.interpret('tool_advice/v1', [item], {'a':{'status':'proposal','selected_id':'search'}})
        self.assertEqual(out['a']['advice']['tool_id'], 'search')
        self.assertFalse(out['a']['advice']['execute'])
        refused = recipes.interpret('tool_advice/v1', [item], {'a':{'status':'abstain','selected_id':None}})
        self.assertIsNone(refused['a']['advice']['tool_id'])
        for bad in ([], [dict(option_id='uncertain', description='bad')],
                    [dict(option_id='x', description='a')]*2):
            with self.assertRaises(ReflexError):
                recipes.prepare('tool_advice/v1','p',True,[item|{'eligible_tools':bad}])

    def test_triage_labels_are_investigation_advice_not_diagnosis(self):
        for recipe, extra, selected in [('failure_triage/v1',{'expected':'Tests pass.'},'environment'),
                                        ('change_impact/v1',{'goal':'Review patch.'},'concurrency')]:
            item = dict(id='a',privacy_namespace='p',text='Small selected packet.',**extra)
            expanded = recipes.prepare(recipe,'p',True,[item])
            self.assertIn(selected, expanded[0]['choices'])
            out = recipes.interpret(recipe,[item],{'a':dict(status='proposal',selected_id=selected)})
            self.assertEqual(out['a']['advice']['investigate'],selected)
            self.assertFalse(out['a']['advice']['verified'])
            with self.assertRaises(ReflexError):
                recipes.prepare(recipe,'p',True,[item|{'unexpected':'value'}])


if __name__ == '__main__': unittest.main()
